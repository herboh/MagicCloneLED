#!/usr/bin/env python3
"""
FastAPI LED Bulb Controller
A modern web API for controlling MagicHome LED bulbs
"""

import os
import json
import socket
import asyncio
from typing import Dict, List, Optional, Union
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn


# Pydantic Models
class BulbStatus(BaseModel):
    name: str
    online: bool
    on: bool = False
    red: int = 0
    green: int = 0
    blue: int = 0
    warm_white: int = 0
    brightness_percent: int = 0
    color_hex: str = "#000000"
    color_name: str = "black"


class BulbCommand(BaseModel):
    action: str = Field(
        ..., description="Action: on, off, toggle, color, brightness, warm_white"
    )
    color: Optional[str] = Field(None, description="Hex color code or color name")
    brightness: Optional[int] = Field(
        None, ge=0, le=100, description="Brightness percentage 0-100"
    )
    warm_white: Optional[int] = Field(
        None, ge=0, le=100, description="Warm white percentage 0-100"
    )


class GroupCommand(BaseModel):
    targets: List[str] = Field(..., description="List of bulb names or group names")
    action: str = Field(..., description="Action to perform")
    color: Optional[str] = None
    brightness: Optional[int] = Field(None, ge=0, le=100)
    warm_white: Optional[int] = Field(None, ge=0, le=100)


# Configuration Loading
def load_config():
    """Load configuration from config.json or environment variables"""
    config_path = os.path.join(os.path.dirname(__file__), "config.json")

    # Try loading from file first
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback to environment variables or default config
        return {
            "bulbs": json.loads(os.getenv("LED_BULBS", "{}")),
            "groups": json.loads(os.getenv("LED_GROUPS", "{}")),
            "colors": json.loads(os.getenv("LED_COLORS", "{}")),
        }


CONFIG = load_config()
BULBS = CONFIG.get("bulbs", {})
GROUPS = CONFIG.get("groups", {})
COLORS = CONFIG.get("colors", {})


class LEDController:
    def __init__(self, ip: str, port: int = 5577):
        self.ip = ip
        self.port = port

    async def send_command(self, data: List[int]) -> bool:
        """Send command to LED bulb asynchronously"""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.ip, self.port), timeout=3.0
            )
            writer.write(bytes(data))
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            return True
        except Exception as e:
            print(f"Failed to send command to {self.ip}: {e}")
            return False

    def checksum(self, data: List[int]) -> int:
        """Calculate checksum"""
        return sum(data) & 0xFF

    async def power_on(self) -> bool:
        """Turn on bulb"""
        cmd = [0x71, 0x23, 0x0F]
        cmd.append(self.checksum(cmd))
        return await self.send_command(cmd)

    async def power_off(self) -> bool:
        """Turn off bulb"""
        cmd = [0x71, 0x24, 0x0F]
        cmd.append(self.checksum(cmd))
        return await self.send_command(cmd)

    async def set_rgb(self, red: int, green: int, blue: int) -> bool:
        """Set RGB color (automatically turns on bulb)"""
        cmd = [0x31, red, green, blue, 0x00, 0x00, 0xF0, 0x0F]
        cmd.append(self.checksum(cmd))
        return await self.send_command(cmd)

    async def set_warm_white(self, brightness: int = 255) -> bool:
        """Set warm white (automatically turns on bulb)"""
        cmd = [0x31, 0x00, 0x00, 0x00, brightness, 0x00, 0x0F, 0xF0]
        cmd.append(self.checksum(cmd))
        return await self.send_command(cmd)

    def apply_brightness_to_rgb(
        self, r: int, g: int, b: int, brightness_percent: int
    ) -> tuple:
        """Apply brightness percentage to RGB values"""
        scale = brightness_percent / 100.0
        return int(r * scale), int(g * scale), int(b * scale)

    def hex_to_rgb(self, hex_color: str) -> tuple:
        """Convert hex to RGB tuple"""
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    def rgb_to_hex(self, r: int, g: int, b: int) -> str:
        """Convert RGB to hex string"""
        return f"#{r:02x}{g:02x}{b:02x}".upper()

    async def query_status(self) -> Optional[Dict]:
        """Query bulb status asynchronously"""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.ip, self.port), timeout=3.0
            )

            query_cmd = [0x81, 0x8A, 0x8B, 0x96]
            writer.write(bytes(query_cmd))
            await writer.drain()

            response = await asyncio.wait_for(reader.read(1024), timeout=2.0)
            writer.close()
            await writer.wait_closed()

            if len(response) >= 14:
                return {
                    "on": response[2] == 0x23,
                    "red": response[6],
                    "green": response[7],
                    "blue": response[8],
                    "warm_white": response[9],
                }
        except Exception as e:
            print(f"Failed to query status from {self.ip}: {e}")

        return None

    async def set_brightness_only(self, brightness_percent: int) -> bool:
        """Change brightness while preserving current color"""
        status = await self.query_status()

        if not status or not status["on"]:
            # If bulb is off, turn on as white at requested brightness
            r, g, b = self.apply_brightness_to_rgb(255, 255, 255, brightness_percent)
            return await self.set_rgb(r, g, b)

        if status["warm_white"] > 0:
            # Currently in warm white mode
            brightness_val = int((brightness_percent * 255) / 100)
            return await self.set_warm_white(brightness_val)
        else:
            # Currently in RGB mode - preserve color
            max_val = max(status["red"], status["green"], status["blue"])
            if max_val == 0:
                r, g, b = self.apply_brightness_to_rgb(
                    255, 255, 255, brightness_percent
                )
            else:
                # Scale back to full brightness, then apply new brightness
                scale = 255.0 / max_val
                full_r = min(255, int(status["red"] * scale))
                full_g = min(255, int(status["green"] * scale))
                full_b = min(255, int(status["blue"] * scale))
                r, g, b = self.apply_brightness_to_rgb(
                    full_r, full_g, full_b, brightness_percent
                )

            return await self.set_rgb(r, g, b)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                # Remove dead connections
                self.disconnect(connection)


# Global connection manager
manager = ConnectionManager()


# FastAPI App Setup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("LED Controller API starting up...")
    print(f"Found {len(BULBS)} bulbs: {list(BULBS.keys())}")
    print(f"Found {len(GROUPS)} groups: {list(GROUPS.keys())}")
    yield
    # Shutdown
    print("LED Controller API shutting down...")


app = FastAPI(
    title="LED Bulb Controller API",
    description="Modern web API for controlling MagicHome LED bulbs",
    version="2.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helper Functions
def get_target_bulbs(target: str) -> List[tuple]:
    """Get list of (name, ip) tuples for target"""
    if target in BULBS:
        return [(target, BULBS[target])]
    elif target in GROUPS:
        return [(name, BULBS[name]) for name in GROUPS[target] if name in BULBS]
    else:
        return []


def get_color_name(hex_color: str) -> str:
    """Get color name from hex value"""
    hex_upper = hex_color.upper()
    return next(
        (name for name, hex_val in COLORS.items() if hex_val.upper() == hex_upper),
        hex_color,
    )


async def format_bulb_status(name: str, ip: str) -> BulbStatus:
    """Get formatted status for a bulb"""
    led = LEDController(ip)
    status = await led.query_status()

    if not status:
        return BulbStatus(name=name, online=False)

    # Calculate brightness and color info
    if status["warm_white"] > 0:
        brightness_pct = int((status["warm_white"] * 100) / 255)
        color_hex = "#FFFFFF"  # Warm white shows as white
        color_name = "warm white"
    else:
        brightness_pct = int(
            (max(status["red"], status["green"], status["blue"]) * 100) / 255
        )
        color_hex = (
            f"#{status['red']:02x}{status['green']:02x}{status['blue']:02x}".upper()
        )
        color_name = get_color_name(color_hex)

    return BulbStatus(
        name=name,
        online=True,
        on=status["on"],
        red=status["red"],
        green=status["green"],
        blue=status["blue"],
        warm_white=status["warm_white"],
        brightness_percent=brightness_pct,
        color_hex=color_hex,
        color_name=color_name,
    )


# API Routes
@app.get("/")
async def root():
    return {
        "message": "LED Bulb Controller API",
        "version": "2.0.0",
        "endpoints": {
            "bulbs": "/bulbs",
            "groups": "/groups",
            "colors": "/colors",
            "docs": "/docs",
        },
    }


@app.get("/bulbs", response_model=List[BulbStatus])
async def get_all_bulbs():
    """Get status of all bulbs"""
    tasks = [format_bulb_status(name, ip) for name, ip in BULBS.items()]
    return await asyncio.gather(*tasks)


@app.get("/bulbs/{bulb_name}", response_model=BulbStatus)
async def get_bulb_status(bulb_name: str):
    """Get status of a specific bulb"""
    if bulb_name not in BULBS:
        raise HTTPException(status_code=404, detail="Bulb not found")

    return await format_bulb_status(bulb_name, BULBS[bulb_name])


@app.post("/bulbs/{bulb_name}/command")
async def control_bulb(bulb_name: str, command: BulbCommand):
    """Send command to a specific bulb"""
    if bulb_name not in BULBS:
        raise HTTPException(status_code=404, detail="Bulb not found")

    led = LEDController(BULBS[bulb_name])
    success = False

    try:
        if command.action == "on":
            success = await led.power_on()
        elif command.action == "off":
            success = await led.power_off()
        elif command.action == "toggle":
            status = await led.query_status()
            if status and status["on"]:
                success = await led.power_off()
            else:
                success = await led.power_on()
        elif command.action == "color" and command.color:
            if command.color.upper() in ["WW", "WARMWHITE", "WARM"]:
                brightness = command.brightness or 100
                brightness_val = int((brightness * 255) / 100)
                success = await led.set_warm_white(brightness_val)
            else:
                # Handle hex colors or named colors
                color_hex = COLORS.get(command.color.lower(), command.color)
                r, g, b = led.hex_to_rgb(color_hex)

                if command.brightness is not None:
                    r, g, b = led.apply_brightness_to_rgb(r, g, b, command.brightness)

                success = await led.set_rgb(r, g, b)
        elif command.action == "brightness" and command.brightness is not None:
            success = await led.set_brightness_only(command.brightness)
        elif command.action == "warm_white":
            brightness = command.warm_white or command.brightness or 100
            brightness_val = int((brightness * 255) / 100)
            success = await led.set_warm_white(brightness_val)
        else:
            raise HTTPException(
                status_code=400, detail="Invalid command or missing parameters"
            )

        if not success:
            raise HTTPException(
                status_code=500, detail="Failed to send command to bulb"
            )

        # Get updated status and broadcast to WebSocket clients
        updated_status = await format_bulb_status(bulb_name, BULBS[bulb_name])
        await manager.broadcast({"type": "bulb_update", "data": updated_status.dict()})

        return updated_status

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Command failed: {str(e)}")


@app.post("/groups/command")
async def control_group(command: GroupCommand):
    """Send command to multiple bulbs/groups"""
    all_bulbs = []

    # Resolve all target bulbs
    for target in command.targets:
        bulbs = get_target_bulbs(target)
        if not bulbs:
            raise HTTPException(status_code=404, detail=f"Target not found: {target}")
        all_bulbs.extend(bulbs)

    # Remove duplicates while preserving order
    unique_bulbs = []
    seen = set()
    for name, ip in all_bulbs:
        if name not in seen:
            unique_bulbs.append((name, ip))
            seen.add(name)

    # Execute commands in parallel
    tasks = []
    for name, ip in unique_bulbs:
        bulb_command = BulbCommand(
            action=command.action,
            color=command.color,
            brightness=command.brightness,
            warm_white=command.warm_white,
        )
        tasks.append(control_single_bulb(name, ip, bulb_command))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Collect successful results
    successful_updates = []
    errors = []

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            errors.append(f"{unique_bulbs[i][0]}: {str(result)}")
        else:
            successful_updates.append(result)

    # Broadcast updates
    if successful_updates:
        await manager.broadcast({"type": "group_update", "data": successful_updates})

    return {
        "success": len(successful_updates),
        "failed": len(errors),
        "errors": errors,
        "updated_bulbs": successful_updates,
    }


async def control_single_bulb(name: str, ip: str, command: BulbCommand) -> BulbStatus:
    """Helper function to control a single bulb"""
    led = LEDController(ip)
    success = False

    if command.action == "on":
        success = await led.power_on()
    elif command.action == "off":
        success = await led.power_off()
    elif command.action == "toggle":
        status = await led.query_status()
        if status and status["on"]:
            success = await led.power_off()
        else:
            success = await led.power_on()
    elif command.action == "color" and command.color:
        if command.color.upper() in ["WW", "WARMWHITE", "WARM"]:
            brightness = command.brightness or 100
            brightness_val = int((brightness * 255) / 100)
            success = await led.set_warm_white(brightness_val)
        else:
            color_hex = COLORS.get(command.color.lower(), command.color)
            r, g, b = led.hex_to_rgb(color_hex)

            if command.brightness is not None:
                r, g, b = led.apply_brightness_to_rgb(r, g, b, command.brightness)

            success = await led.set_rgb(r, g, b)
    elif command.action == "brightness" and command.brightness is not None:
        success = await led.set_brightness_only(command.brightness)
    elif command.action == "warm_white":
        brightness = command.warm_white or command.brightness or 100
        brightness_val = int((brightness * 255) / 100)
        success = await led.set_warm_white(brightness_val)

    if not success:
        raise Exception("Failed to send command")

    return await format_bulb_status(name, ip)


@app.get("/groups")
async def get_groups():
    """Get all available groups"""
    return {"groups": GROUPS, "bulbs": BULBS}


@app.get("/colors")
async def get_colors():
    """Get all available color presets"""
    return {"colors": COLORS}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        # Send initial status
        bulb_statuses = await asyncio.gather(
            *[format_bulb_status(name, ip) for name, ip in BULBS.items()]
        )

        await websocket.send_json(
            {
                "type": "initial_status",
                "data": [status.dict() for status in bulb_statuses],
            }
        )

        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            # Echo back for heartbeat
            await websocket.send_json({"type": "pong", "data": data})

    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")

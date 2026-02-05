#!/usr/bin/env python3
"""
LED Controller FastAPI Server
Slim routes-only implementation with HSV color support
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from bulb_manager import BulbManager
from color_utils import hex_to_hsv, hsv_to_hex
import led_controller


# Global debug flag and logger setup
DEBUG_MODE = False
debug_logger = None


def setup_debug_logging(debug_mode: bool):
    """Setup debug logging to file with timestamping"""
    global DEBUG_MODE, debug_logger
    DEBUG_MODE = debug_mode
    
    if not debug_mode:
        return
    
    # Clear existing log file on startup
    log_file = "led_debug.log"
    open(log_file, 'w').close()
    
    # Setup logger
    debug_logger = logging.getLogger('led_debug')
    debug_logger.setLevel(logging.DEBUG)
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler  
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # Formatter with timestamp
    formatter = logging.Formatter('%(asctime)s.%(msecs)03d | %(message)s', 
                                 datefmt='%H:%M:%S')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    debug_logger.addHandler(file_handler)
    debug_logger.addHandler(console_handler)
    debug_logger.info("=== LED Controller Debug Logging Started ===")
    
    # Set debug logger for led_controller module
    led_controller.set_debug_logger(debug_log)


def debug_log(message: str):
    """Log debug message if debug mode is enabled"""
    if DEBUG_MODE and debug_logger:
        debug_logger.info(message)


# Request/Response Models
class ColorCommand(BaseModel):
    action: str = Field(
        ..., description="Action: on, off, toggle, color, hsv, warm_white"
    )
    h: Optional[float] = Field(None, ge=0, le=360, description="HSV Hue 0-360")
    s: Optional[float] = Field(None, ge=0, le=100, description="HSV Saturation 0-100")
    v: Optional[float] = Field(None, ge=0, le=100, description="HSV Value 0-100")
    hex: Optional[str] = Field(None, description="Hex color code")
    brightness: Optional[int] = Field(
        None, ge=1, le=100, description="Warm white brightness 1-100"
    )


class GroupCommand(BaseModel):
    targets: List[str] = Field(..., description="List of bulb names or group names")
    action: str = Field(..., description="Action to perform")
    h: Optional[float] = Field(None, ge=0, le=360)
    s: Optional[float] = Field(None, ge=0, le=100)
    v: Optional[float] = Field(None, ge=0, le=100)
    hex: Optional[str] = None
    brightness: Optional[int] = Field(None, ge=1, le=100)


# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        debug_log(f"WEBSOCKET: New connection established (total: {len(self.active_connections)})")

    def disconnect(self, websocket: WebSocket):
        try:
            self.active_connections.remove(websocket)
            debug_log(f"WEBSOCKET: Connection disconnected (remaining: {len(self.active_connections)})")
        except ValueError:
            pass

    async def broadcast(self, message: dict):
        if len(self.active_connections) > 0:
            debug_log(f"WEBSOCKET: Broadcasting to {len(self.active_connections)} clients: {message}")

        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except (WebSocketDisconnect, RuntimeError, Exception):
                dead_connections.append(connection)

        for dead_conn in dead_connections:
            self.disconnect(dead_conn)


# Global instances
bulb_manager: Optional[BulbManager] = None
websocket_manager = ConnectionManager()


# Rate limiting with simple request debouncing
request_cache = {}
DEBOUNCE_MS = 120
ACTION_DEBOUNCE_MS = {
    "hsv": 90,
    "color": 90,
    "warm_white": 120,
    "toggle": 120,
    "on": 120,
    "off": 120,
}


def should_process_request(bulb_name: str, action: str) -> bool:
    """Simple debouncing to prevent request flooding"""
    key = f"{bulb_name}:{action}"
    now = time.time() * 1000
    debounce_ms = ACTION_DEBOUNCE_MS.get(action, DEBOUNCE_MS)

    if key in request_cache:
        if now - request_cache[key] < debounce_ms:
            return False

    request_cache[key] = now
    return True


# WebSocket subscriber callback
async def on_bulb_state_change(bulb_state):
    """Notify WebSocket clients of bulb state changes"""
    await websocket_manager.broadcast(
        {"type": "bulb_update", "data": bulb_state.to_dict()}
    )


# App lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    global bulb_manager

    # Startup
    bulb_manager = BulbManager()
    bulb_manager.subscribe(on_bulb_state_change)

    # Initial state refresh
    await bulb_manager.refresh_all()

    # Start background polling
    await bulb_manager.start_background_polling()

    print(f"LED Controller started - {len(bulb_manager.bulbs)} bulbs loaded")

    yield

    # Shutdown
    if bulb_manager:
        await bulb_manager.stop_background_polling()
    print("LED Controller shutting down")


# FastAPI App
app = FastAPI(
    title="LED Controller API",
    description="HSV-based LED bulb control with WebSocket updates",
    version="3.0.0",
    lifespan=lifespan,
)

# CORS middleware for local network access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Routes
@app.get("/")
async def root():
    return {"message": "LED Controller API v3.0", "color_system": "HSV"}


@app.get("/bulbs")
async def get_bulbs():
    """Get all bulb states"""
    if not bulb_manager:
        raise HTTPException(status_code=503, detail="Bulb manager not initialized")

    try:
        return bulb_manager.get_all_states()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/bulbs/{bulb_name}")
async def get_bulb(bulb_name: str):
    """Get specific bulb state"""
    if not bulb_manager:
        raise HTTPException(status_code=503, detail="Bulb manager not initialized")

    bulb = bulb_manager.get_bulb_state(bulb_name)
    if not bulb:
        raise HTTPException(status_code=404, detail="Bulb not found")
    return bulb.to_dict()


@app.post("/bulbs/{bulb_name}/command")
async def control_bulb(bulb_name: str, command: ColorCommand):
    """Control individual bulb with HSV support"""
    debug_log(f"API: POST /bulbs/{bulb_name}/command - {command.dict()}")
    
    if not bulb_manager:
        raise HTTPException(status_code=503, detail="Bulb manager not initialized")

    if not should_process_request(bulb_name, command.action):
        debug_log(f"API: Request debounced for {bulb_name}:{command.action}")
        return {"message": "Request debounced", "bulb": bulb_name}

    if bulb_name not in bulb_manager.bulbs:
        debug_log(f"API: Bulb '{bulb_name}' not found")
        raise HTTPException(status_code=404, detail="Bulb not found")

    success = False

    try:
        if command.action == "on":
            success = await bulb_manager.set_power(bulb_name, True)

        elif command.action == "off":
            success = await bulb_manager.set_power(bulb_name, False)

        elif command.action == "toggle":
            current_state = bulb_manager.get_bulb_state(bulb_name)
            if current_state:
                success = await bulb_manager.set_power(bulb_name, not current_state.on)

        elif command.action == "hsv" and all(
            x is not None for x in [command.h, command.s, command.v]
        ):
            success = await bulb_manager.set_hsv(bulb_name, command.h, command.s, command.v)

        elif command.action == "color" and command.hex:
            h, s, v = hex_to_hsv(command.hex)
            success = await bulb_manager.set_hsv(bulb_name, h, s, v)

        elif command.action == "warm_white" and command.brightness:
            success = await bulb_manager.set_warm_white(bulb_name, command.brightness)

        else:
            raise HTTPException(status_code=400, detail="Invalid command parameters")

        if not success:
            debug_log(f"API: Command failed for {bulb_name} - action: {command.action}")
            raise HTTPException(status_code=500, detail="Command failed")

        result = {
            "message": f"Command executed",
            "bulb": bulb_name,
            "action": command.action,
        }
        debug_log(f"API: Command successful for {bulb_name} - {result}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/groups/command")
async def control_group(command: GroupCommand):
    """Control multiple bulbs/groups with HSV support"""
    debug_log(f"API: POST /groups/command - {command.dict()}")
    
    if not bulb_manager:
        raise HTTPException(status_code=503, detail="Bulb manager not initialized")

    try:
        results = {}
        targets = bulb_manager.resolve_targets(command.targets)
        if not targets:
            raise HTTPException(status_code=400, detail="No valid bulbs in targets")
        active_targets = [
            target for target in targets if should_process_request(target, command.action)
        ]
        if not active_targets:
            return {"message": "Request debounced", "targets": targets}

        if command.action in ["on", "off"]:
            power_state = command.action == "on"
            for target in active_targets:
                results[target] = await bulb_manager.set_power(target, power_state)

        elif command.action == "toggle":
            for target in active_targets:
                current_state = bulb_manager.get_bulb_state(target)
                if current_state:
                    results[target] = await bulb_manager.set_power(
                        target, not current_state.on
                    )

        elif command.action == "hsv" and all(
            x is not None for x in [command.h, command.s, command.v]
        ):
            results = await bulb_manager.set_group_hsv(
                active_targets, command.h, command.s, command.v
            )

        elif command.action == "color" and command.hex:
            h, s, v = hex_to_hsv(command.hex)
            results = await bulb_manager.set_group_hsv(active_targets, h, s, v)

        elif command.action == "warm_white" and command.brightness:
            for target in active_targets:
                results[target] = await bulb_manager.set_warm_white(
                    target, command.brightness
                )
        else:
            raise HTTPException(status_code=400, detail="Invalid command parameters")

        result = {"message": "Group command executed", "results": results}
        debug_log(f"API: Group command successful - {result}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/groups")
async def get_groups():
    """Get available groups and bulbs"""
    if not bulb_manager:
        raise HTTPException(status_code=503, detail="Bulb manager not initialized")

    return {
        "groups": bulb_manager.get_groups(),
        "bulbs": list(bulb_manager.bulbs.keys()),
    }


@app.post("/bulbs/sync")
async def force_sync():
    """Force refresh all bulb states from physical devices"""
    debug_log("API: POST /bulbs/sync - Force refresh requested")
    
    if not bulb_manager:
        raise HTTPException(status_code=503, detail="Bulb manager not initialized")

    try:
        results = await bulb_manager.force_refresh_all()
        success_count = sum(results.values())
        result = {
            "message": f"Synced {success_count}/{len(results)} bulbs",
            "results": results,
        }
        debug_log(f"API: Sync completed - {result}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time bulb state updates"""
    await websocket_manager.connect(websocket)

    try:
        # Send initial state
        if bulb_manager:
            initial_state = bulb_manager.get_all_states()
            initial_msg = {"type": "initial_state", "data": initial_state}
            debug_log(f"WEBSOCKET: Sending initial state to new client: {len(initial_state)} bulbs")
            await websocket.send_json(initial_msg)

        # Keep connection alive
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                debug_log(f"WEBSOCKET: Received from client: {data}")
                await websocket.send_json({"type": "pong", "data": "alive"})
            except asyncio.TimeoutError:
                debug_log("WEBSOCKET: Sending ping to client")
                await websocket.send_json({"type": "ping"})

    except WebSocketDisconnect:
        debug_log("WEBSOCKET: Client disconnected normally")
        pass
    except Exception as e:
        debug_log(f"WEBSOCKET: Error occurred: {e}")
        print(f"WebSocket error: {e}")
    finally:
        websocket_manager.disconnect(websocket)


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='LED Controller FastAPI Server')
    parser.add_argument('--debug', '--verbose', action='store_true', 
                       help='Enable debug logging to file and console')
    args = parser.parse_args()
    
    # Setup debug logging
    setup_debug_logging(args.debug)
    
    if args.debug:
        print("Debug logging enabled - writing to led_debug.log and console")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disabled for production stability
        log_level="info",
        access_log=False,  # Reduce log spam
    )

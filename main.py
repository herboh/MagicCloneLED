#!/usr/bin/env python3
"""
LED Controller FastAPI Server
Slim routes-only implementation with HSV color support
"""

import asyncio
import json
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from services.bulb_manager import BulbManager
from utils.color_utils import hex_to_hsv, hsv_to_hex


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

    def disconnect(self, websocket: WebSocket):
        try:
            self.active_connections.remove(websocket)
        except ValueError:
            pass

    async def broadcast(self, message: dict):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                dead_connections.append(connection)

        for dead_conn in dead_connections:
            self.disconnect(dead_conn)


# Global instances - Fixed type annotation
bulb_manager: Optional[BulbManager] = None
websocket_manager = ConnectionManager()


# Rate limiting with simple request debouncing
request_cache = {}
DEBOUNCE_MS = 100


def should_process_request(bulb_name: str, action: str) -> bool:
    """Simple debouncing to prevent request flooding"""
    import time

    key = f"{bulb_name}:{action}"
    now = time.time() * 1000

    if key in request_cache:
        if now - request_cache[key] < DEBOUNCE_MS:
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

# Security middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
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
    if not bulb_manager:
        raise HTTPException(status_code=503, detail="Bulb manager not initialized")

    if not should_process_request(bulb_name, command.action):
        return {"message": "Request debounced", "bulb": bulb_name}

    if bulb_name not in bulb_manager.bulbs:
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
            # Type guard ensures these are not None at this point
            h = command.h if command.h is not None else 0
            s = command.s if command.s is not None else 0
            v = command.v if command.v is not None else 0
            success = await bulb_manager.set_hsv(bulb_name, h, s, v)

        elif command.action == "color" and command.hex:
            h, s, v = hex_to_hsv(command.hex)
            success = await bulb_manager.set_hsv(bulb_name, h, s, v)

        elif command.action == "warm_white" and command.brightness:
            success = await bulb_manager.set_warm_white(bulb_name, command.brightness)

        else:
            raise HTTPException(status_code=400, detail="Invalid command parameters")

        if not success:
            raise HTTPException(status_code=500, detail="Command failed")

        return {
            "message": f"Command executed",
            "bulb": bulb_name,
            "action": command.action,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/groups/command")
async def control_group(command: GroupCommand):
    """Control multiple bulbs/groups with HSV support"""
    if not bulb_manager:
        raise HTTPException(status_code=503, detail="Bulb manager not initialized")

    try:
        results = {}

        if command.action in ["on", "off"]:
            power_state = command.action == "on"
            for target in command.targets:
                if target in bulb_manager.bulbs:
                    results[target] = await bulb_manager.set_power(target, power_state)
                elif target in bulb_manager.groups:
                    for bulb_name in bulb_manager.groups[target]:
                        results[bulb_name] = await bulb_manager.set_power(
                            bulb_name, power_state
                        )

        elif command.action == "hsv" and all(
            x is not None for x in [command.h, command.s, command.v]
        ):
            # Type guard ensures these are not None at this point
            h = command.h if command.h is not None else 0
            s = command.s if command.s is not None else 0
            v = command.v if command.v is not None else 0
            results = await bulb_manager.set_group_hsv(command.targets, h, s, v)

        elif command.action == "color" and command.hex:
            h, s, v = hex_to_hsv(command.hex)
            results = await bulb_manager.set_group_hsv(command.targets, h, s, v)

        elif command.action == "warm_white" and command.brightness:
            for target in command.targets:
                if target in bulb_manager.bulbs:
                    results[target] = await bulb_manager.set_warm_white(
                        target, command.brightness
                    )
                elif target in bulb_manager.groups:
                    for bulb_name in bulb_manager.groups[target]:
                        results[bulb_name] = await bulb_manager.set_warm_white(
                            bulb_name, command.brightness
                        )

        return {"message": "Group command executed", "results": results}

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
    if not bulb_manager:
        raise HTTPException(status_code=503, detail="Bulb manager not initialized")

    try:
        results = await bulb_manager.force_refresh_all()
        success_count = sum(results.values())
        return {
            "message": f"Synced {success_count}/{len(results)} bulbs",
            "results": results,
        }
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
            await websocket.send_json({"type": "initial_state", "data": initial_state})

        # Keep connection alive
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                await websocket.send_json({"type": "pong", "data": "alive"})
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        websocket_manager.disconnect(websocket)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disabled for production stability
        log_level="info",
        access_log=False,  # Reduce log spam
    )


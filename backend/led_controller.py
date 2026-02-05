"""
Simple LED Controller for MagicHome BL606A bulbs
Pure TCP communication with minimal complexity
"""

import asyncio
from typing import Optional, Dict

# Debug logging function - will be overridden by main.py
debug_log_func = None

def debug_log(msg: str):
    if debug_log_func:
        debug_log_func(msg)

def set_debug_logger(logger_func):
    """Set debug logging function"""
    global debug_log_func
    debug_log_func = logger_func


class LEDController:
    def __init__(self, ip: str, port: int = 5577):
        self.ip = ip
        self.port = port
        self._lock = asyncio.Lock()

    async def _send_command(self, data: list[int]) -> bool:
        """Send raw command bytes to bulb"""
        debug_log(f"BULB {self.ip}: Sending command bytes: {data}")
        async with self._lock:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self.ip, self.port), timeout=3.0
                )
                try:
                    writer.write(bytes(data))
                    await writer.drain()
                finally:
                    writer.close()
                    await writer.wait_closed()
                debug_log(f"BULB {self.ip}: Command sent successfully")
                return True
            except Exception as e:
                debug_log(f"BULB {self.ip}: Command failed: {e}")
                return False

    def _checksum(self, data: list[int]) -> int:
        """Calculate simple checksum"""
        return sum(data) & 0xFF

    async def power_on(self) -> bool:
        """Turn bulb on"""
        debug_log(f"BULB {self.ip}: Power ON command")
        cmd = [0x71, 0x23, 0x0F]
        cmd.append(self._checksum(cmd))
        return await self._send_command(cmd)

    async def power_off(self) -> bool:
        """Turn bulb off"""
        debug_log(f"BULB {self.ip}: Power OFF command")
        cmd = [0x71, 0x24, 0x0F]
        cmd.append(self._checksum(cmd))
        return await self._send_command(cmd)

    async def set_rgb(self, r: int, g: int, b: int) -> bool:
        """Set RGB color (0-255 each)"""
        debug_log(f"BULB {self.ip}: Set RGB({r}, {g}, {b})")
        cmd = [0x31, r, g, b, 0x00, 0x00, 0xF0, 0x0F]
        cmd.append(self._checksum(cmd))
        return await self._send_command(cmd)

    async def set_warm_white(self, brightness: int = 255) -> bool:
        """Set warm white mode (0-255 brightness)"""
        debug_log(f"BULB {self.ip}: Set warm white brightness={brightness}")
        cmd = [0x31, 0x00, 0x00, 0x00, brightness, 0x00, 0x0F, 0xF0]
        cmd.append(self._checksum(cmd))
        return await self._send_command(cmd)

    async def get_status(self) -> Optional[Dict]:
        """Query current bulb status"""
        debug_log(f"BULB {self.ip}: Requesting status")
        async with self._lock:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self.ip, self.port), timeout=3.0
                )

                try:
                    # Status query
                    query = [0x81, 0x8A, 0x8B, 0x96]
                    debug_log(f"BULB {self.ip}: Sending status query: {query}")
                    writer.write(bytes(query))
                    await writer.drain()

                    # Read response
                    response = await asyncio.wait_for(reader.read(1024), timeout=2.0)
                finally:
                    writer.close()
                    await writer.wait_closed()

                if len(response) >= 14:
                    status = {
                        "online": True,
                        "on": response[2] == 0x23,
                        "r": response[6],
                        "g": response[7],
                        "b": response[8],
                        "warm_white": response[9],
                    }
                    debug_log(f"BULB {self.ip}: Status response: {status} (raw bytes: {list(response[:14])})")
                    return status
            except Exception as e:
                debug_log(f"BULB {self.ip}: Status query failed: {e}")

        offline_status = {"online": False, "on": False, "r": 0, "g": 0, "b": 0, "warm_white": 0}
        debug_log(f"BULB {self.ip}: Returning offline status: {offline_status}")
        return offline_status

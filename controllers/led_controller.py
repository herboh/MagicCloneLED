"""
Simple LED Controller for MagicHome BL606A bulbs
Pure TCP communication with minimal complexity
"""

import asyncio
from typing import Optional, Dict


class LEDController:
    def __init__(self, ip: str, port: int = 5577):
        self.ip = ip
        self.port = port

    async def _send_command(self, data: list[int]) -> bool:
        """Send raw command bytes to bulb"""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.ip, self.port), timeout=3.0
            )
            writer.write(bytes(data))
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    def _checksum(self, data: list[int]) -> int:
        """Calculate simple checksum"""
        return sum(data) & 0xFF

    async def power_on(self) -> bool:
        """Turn bulb on"""
        cmd = [0x71, 0x23, 0x0F]
        cmd.append(self._checksum(cmd))
        return await self._send_command(cmd)

    async def power_off(self) -> bool:
        """Turn bulb off"""
        cmd = [0x71, 0x24, 0x0F]
        cmd.append(self._checksum(cmd))
        return await self._send_command(cmd)

    async def set_rgb(self, r: int, g: int, b: int) -> bool:
        """Set RGB color (0-255 each)"""
        cmd = [0x31, r, g, b, 0x00, 0x00, 0xF0, 0x0F]
        cmd.append(self._checksum(cmd))
        return await self._send_command(cmd)

    async def set_warm_white(self, brightness: int = 255) -> bool:
        """Set warm white mode (0-255 brightness)"""
        cmd = [0x31, 0x00, 0x00, 0x00, brightness, 0x00, 0x0F, 0xF0]
        cmd.append(self._checksum(cmd))
        return await self._send_command(cmd)

    async def get_status(self) -> Optional[Dict]:
        """Query current bulb status"""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.ip, self.port), timeout=3.0
            )

            # Status query
            query = [0x81, 0x8A, 0x8B, 0x96]
            writer.write(bytes(query))
            await writer.drain()

            # Read response
            response = await asyncio.wait_for(reader.read(1024), timeout=2.0)
            writer.close()
            await writer.wait_closed()

            if len(response) >= 14:
                return {
                    "online": True,
                    "on": response[2] == 0x23,
                    "r": response[6],
                    "g": response[7],
                    "b": response[8],
                    "warm_white": response[9],
                }
        except Exception:
            pass

        return {"online": False, "on": False, "r": 0, "g": 0, "b": 0, "warm_white": 0}


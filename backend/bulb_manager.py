"""
Bulb state management service
Centralized state with efficient caching and updates
"""

import asyncio
import json
from typing import Awaitable, Callable, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from led_controller import LEDController
from color_utils import rgb_to_hsv, hsv_to_rgb, rgb_to_hex


@dataclass
class BulbState:
    """Simple bulb state representation"""

    name: str
    ip: str
    online: bool = False
    on: bool = False
    r: int = 0
    g: int = 0
    b: int = 0
    warm_white: int = 0
    h: float = 0.0  # HSV hue 0-360
    s: float = 0.0  # HSV saturation 0-100
    v: float = 0.0  # HSV value 0-100
    last_updated: Optional[datetime] = None
    last_command_time: Optional[datetime] = None
    poll_interval: int = 60  # Initial polling interval in seconds
    consecutive_failures: int = 0

    def to_dict(self) -> dict:
        """Convert to API-friendly dict"""
        return {
            "name": self.name,
            "online": self.online,
            "on": self.on,
            "r": self.r,
            "g": self.g,
            "b": self.b,
            "warm_white": self.warm_white,
            "h": round(self.h, 1),
            "s": round(self.s, 1),
            "v": round(self.v, 1),
            "hex": rgb_to_hex(self.r, self.g, self.b),
            "brightness": int(self.v)
            if not self.warm_white
            else int((self.warm_white / 255) * 100),
            "is_warm_white": self.warm_white > 0,
        }


class BulbManager:
    """Manages bulb states and communications"""
    MIN_COMMAND_INTERVAL_SECONDS = 0.12
    GROUP_COMMAND_SPACING_SECONDS = 0.02

    def __init__(self, config_path: str = "../config.json"):
        self.bulbs: Dict[str, BulbState] = {}
        self.groups: Dict[str, List[str]] = {}
        self.controllers: Dict[str, LEDController] = {}
        self.command_locks: Dict[str, asyncio.Lock] = {}
        self.last_transport_command: Dict[str, float] = {}
        self.subscribers: List[Callable] = []
        self.polling_task: Optional[asyncio.Task] = None
        self.polling_enabled = False
        self._load_config(config_path)
        self._setup_controllers()

    def _load_config(self, config_path: str):
        """Load bulbs and groups from config"""
        try:
            with open(config_path, "r") as f:
                config = json.load(f)

            # Initialize bulb states
            for name, ip in config.get("bulbs", {}).items():
                self.bulbs[name] = BulbState(name=name, ip=ip)

            # Store groups
            self.groups = config.get("groups", {})

        except FileNotFoundError:
            print(f"ERROR: Config file {config_path} not found - bulb manager will have no bulbs")
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in config file {config_path}: {e}")

    def _setup_controllers(self):
        """Create LED controllers for each bulb"""
        for name, bulb in self.bulbs.items():
            self.controllers[name] = LEDController(bulb.ip)
            self.command_locks[name] = asyncio.Lock()
            self.last_transport_command[name] = 0.0

    def resolve_targets(self, targets: List[str]) -> List[str]:
        """Resolve bulbs/groups to unique bulb names while preserving order"""
        resolved: List[str] = []
        seen = set()

        for target in targets:
            if target in self.bulbs:
                if target not in seen:
                    seen.add(target)
                    resolved.append(target)
            elif target in self.groups:
                for bulb_name in self.groups[target]:
                    if bulb_name in self.bulbs and bulb_name not in seen:
                        seen.add(bulb_name)
                        resolved.append(bulb_name)

        return resolved

    async def _run_serialized_command(
        self, name: str, command: Callable[[LEDController], Awaitable[bool]]
    ) -> bool:
        """Serialize and throttle bulb commands to avoid overloading devices"""
        if name not in self.controllers:
            return False

        lock = self.command_locks[name]
        async with lock:
            loop = asyncio.get_running_loop()
            now = loop.time()
            last_command = self.last_transport_command.get(name, 0.0)
            delay = self.MIN_COMMAND_INTERVAL_SECONDS - (now - last_command)
            if delay > 0:
                await asyncio.sleep(delay)

            success = await command(self.controllers[name])
            self.last_transport_command[name] = loop.time()
            return success

    def subscribe(self, callback: Callable):
        """Subscribe to state changes"""
        self.subscribers.append(callback)

    async def _notify_subscribers(self, bulb_name: str):
        """Notify subscribers of state change"""
        bulb_state = self.bulbs[bulb_name]
        for callback in self.subscribers:
            try:
                await callback(bulb_state)
            except Exception as e:
                print(f"Subscriber notification failed: {e}")

    def _update_hsv_from_rgb(self, bulb: BulbState):
        """Update HSV values from RGB"""
        if bulb.warm_white > 0:
            # Warm white mode
            bulb.h = 0.0
            bulb.s = 0.0
            bulb.v = (bulb.warm_white / 255) * 100
        else:
            # RGB mode
            bulb.h, bulb.s, bulb.v = rgb_to_hsv(bulb.r, bulb.g, bulb.b)

        bulb.last_updated = datetime.now()

    async def refresh_bulb(self, name: str) -> bool:
        """Refresh single bulb state from device"""
        if name not in self.bulbs or name not in self.controllers:
            return False

        bulb = self.bulbs[name]
        
        # Check if a command was sent in the last ~5 seconds, if so ignore poll
        if bulb.last_command_time:
            time_since_command = datetime.now() - bulb.last_command_time
            if time_since_command.total_seconds() < 5:
                return bulb.online  # Return current online status without polling

        controller = self.controllers[name]
        try:
            status = await controller.get_status()
        except asyncio.CancelledError:
            raise
        except Exception:
            # If get_status fails, treat as offline
            status = None

        # If no status (e.g., device offline), mark offline and notify
        if not isinstance(status, dict):
            bulb.online = False
            await self._notify_subscribers(name)
            return False

        # Use .get with sane defaults; keep prior color values if missing
        bulb.online = bool(status.get("online", False))
        bulb.on = bool(status.get("on", False))
        bulb.r = int(status.get("r", bulb.r))
        bulb.g = int(status.get("g", bulb.g))
        bulb.b = int(status.get("b", bulb.b))
        bulb.warm_white = int(status.get("warm_white", bulb.warm_white))

        self._update_hsv_from_rgb(bulb)
        await self._notify_subscribers(name)
        return bulb.online

    async def refresh_all(self) -> Dict[str, bool]:
        """Refresh all bulb states"""
        tasks = [self.refresh_bulb(name) for name in self.bulbs.keys()]
        results = await asyncio.gather(*tasks)
        return dict(zip(self.bulbs.keys(), results))

    async def set_power(self, name: str, on: bool) -> bool:
        """Set bulb power state"""
        if name not in self.controllers:
            return False

        success = await self._run_serialized_command(
            name,
            lambda controller: controller.power_on() if on else controller.power_off(),
        )

        if success:
            bulb = self.bulbs[name]
            bulb.on = on
            bulb.last_command_time = datetime.now()
            await self._notify_subscribers(name)

        return success

    async def set_rgb(self, name: str, r: int, g: int, b: int) -> bool:
        """Set RGB color"""
        if name not in self.controllers:
            return False

        success = await self._run_serialized_command(
            name, lambda controller: controller.set_rgb(r, g, b)
        )

        if success:
            bulb = self.bulbs[name]
            bulb.on = True
            bulb.r = r
            bulb.g = g
            bulb.b = b
            bulb.warm_white = 0
            bulb.last_command_time = datetime.now()
            self._update_hsv_from_rgb(bulb)
            await self._notify_subscribers(name)

        return success

    async def set_hsv(self, name: str, h: float, s: float, v: float) -> bool:
        """Set HSV color"""
        r, g, b = hsv_to_rgb(h, s, v)
        return await self.set_rgb(name, r, g, b)

    async def set_warm_white(self, name: str, brightness: int) -> bool:
        """Set warm white mode (brightness 0-100)"""
        if name not in self.controllers:
            return False

        brightness_255 = int((brightness / 100) * 255)
        success = await self._run_serialized_command(
            name, lambda controller: controller.set_warm_white(brightness_255)
        )

        if success:
            bulb = self.bulbs[name]
            bulb.on = True
            bulb.r = 0
            bulb.g = 0
            bulb.b = 0
            bulb.warm_white = brightness_255
            bulb.last_command_time = datetime.now()
            self._update_hsv_from_rgb(bulb)
            await self._notify_subscribers(name)

        return success

    async def set_group_rgb(
        self, group_names: List[str], r: int, g: int, b: int
    ) -> Dict[str, bool]:
        """Set RGB for multiple bulbs/groups"""
        target_bulbs = self.resolve_targets(group_names)
        results: Dict[str, bool] = {}

        for index, bulb_name in enumerate(target_bulbs):
            results[bulb_name] = await self.set_rgb(bulb_name, r, g, b)
            if index < len(target_bulbs) - 1:
                await asyncio.sleep(self.GROUP_COMMAND_SPACING_SECONDS)

        return results

    async def set_group_hsv(
        self, group_names: List[str], h: float, s: float, v: float
    ) -> Dict[str, bool]:
        """Set HSV for multiple bulbs/groups"""
        r, g, b = hsv_to_rgb(h, s, v)
        return await self.set_group_rgb(group_names, r, g, b)

    def get_bulb_state(self, name: str) -> Optional[BulbState]:
        """Get current bulb state"""
        return self.bulbs.get(name)

    def get_all_states(self) -> List[dict]:
        """Get all bulb states as dicts"""
        return [bulb.to_dict() for bulb in self.bulbs.values()]

    def get_groups(self) -> Dict[str, List[str]]:
        """Get available groups"""
        return self.groups.copy()

    def _should_skip_bulb(self, bulb: BulbState) -> bool:
        """Check if bulb should be skipped from polling (recent activity)"""
        if not bulb.last_command_time:
            return False

        time_since_command = datetime.now() - bulb.last_command_time
        return (
            time_since_command.total_seconds() < 10
        )  # Skip if commanded < 10 seconds ago

    def _update_poll_interval(self, bulb: BulbState, success: bool):
        """Update polling interval based on success/failure with exponential backoff"""
        if success:
            bulb.consecutive_failures = 0
            bulb.poll_interval = 60  # Reset to base interval
        else:
            bulb.consecutive_failures += 1
            # Exponential backoff: 60s → 2min → 5min → 10min (max)
            if bulb.consecutive_failures == 1:
                bulb.poll_interval = 120  # 2 minutes
            elif bulb.consecutive_failures == 2:
                bulb.poll_interval = 300  # 5 minutes
            else:
                bulb.poll_interval = 600  # 10 minutes max

    async def _poll_single_bulb(self, name: str) -> bool:
        """Poll a single bulb and update state"""
        bulb = self.bulbs[name]

        # Skip if recently commanded
        if self._should_skip_bulb(bulb):
            return True

        # Query bulb status
        success = await self.refresh_bulb(name)

        # Update polling interval based on result
        self._update_poll_interval(bulb, success)

        return success

    async def _background_polling_loop(self):
        """Background polling loop with smart scheduling"""
        while self.polling_enabled:
            try:
                current_time = datetime.now()

                # Check each bulb's polling schedule
                poll_tasks = []
                for name, bulb in self.bulbs.items():
                    # Check if it's time to poll this bulb
                    time_since_update = float("inf")
                    if bulb.last_updated:
                        time_since_update = (
                            current_time - bulb.last_updated
                        ).total_seconds()

                    if time_since_update >= bulb.poll_interval:
                        poll_tasks.append(self._poll_single_bulb(name))

                # Execute polls concurrently but with timeout
                if poll_tasks:
                    try:
                        await asyncio.wait_for(
                            asyncio.gather(*poll_tasks, return_exceptions=True),
                            timeout=30.0,  # Total timeout for all polls
                        )
                    except asyncio.TimeoutError:
                        print("Background polling timeout - some bulbs may be offline")

                # Sleep for 10 seconds before next check
                await asyncio.sleep(10)

            except Exception as e:
                print(f"Background polling error: {e}")
                await asyncio.sleep(30)  # Longer sleep on error

    async def start_background_polling(self):
        """Start the background polling task"""
        if self.polling_enabled:
            return  # Already running

        self.polling_enabled = True
        self.polling_task = asyncio.create_task(self._background_polling_loop())
        print("Background bulb polling started")

    async def stop_background_polling(self):
        """Stop the background polling task"""
        self.polling_enabled = False
        if self.polling_task and not self.polling_task.done():
            self.polling_task.cancel()
            try:
                await self.polling_task
            except asyncio.CancelledError:
                pass
        print("Background bulb polling stopped")

    async def force_refresh_all(self) -> Dict[str, bool]:
        """Force refresh all bulbs ignoring skip logic"""
        tasks = []
        for name in self.bulbs.keys():
            tasks.append(self.refresh_bulb(name))

        results = await asyncio.gather(*tasks)
        return dict(zip(self.bulbs.keys(), results))

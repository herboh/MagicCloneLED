#!/usr/bin/env python3
"""
Elegant LED Bulb API
Usage:
  led_api.py lamp                    # Toggle on/off
  led_api.py lamp on/off             # Explicit on/off
  led_api.py lamp red                # Set color
  led_api.py lamp #FF0000            # Set hex color
  led_api.py lamp warmwhite          # Set warm white
  led_api.py lamp 50                 # Set brightness only
"""

import socket
import sys
import json
import os


def load_config():
    """Load configuration from config.json"""
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Config file not found at {config_path}")
        print("Create a config.json file with your bulb settings.")
        sys.exit(1)


# Load configuration
CONFIG = load_config()
BULBS = CONFIG.get("bulbs", {})
GROUPS = CONFIG.get("groups", {})
COLORS = CONFIG.get("colors", {})


class LEDController:
    def __init__(self, ip, port=5577):
        self.ip = ip
        self.port = port

    def send_command(self, data):
        """Send command to LED"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(3)
                sock.connect((self.ip, self.port))
                sock.send(bytes(data))
            return True
        except Exception:
            return False

    def checksum(self, data):
        """Calculate checksum"""
        return sum(data) & 0xFF

    def power_on(self):
        """Turn on (explicit power command)"""
        cmd = [0x71, 0x23, 0x0F]
        cmd.append(self.checksum(cmd))
        return self.send_command(cmd)

    def power_off(self):
        """Turn off"""
        cmd = [0x71, 0x24, 0x0F]
        cmd.append(self.checksum(cmd))
        return self.send_command(cmd)

    def set_rgb(self, red, green, blue):
        """Set RGB color (automatically turns on bulb)"""
        cmd = [0x31, red, green, blue, 0x00, 0x00, 0xF0, 0x0F]
        cmd.append(self.checksum(cmd))
        return self.send_command(cmd)

    def set_warm_white(self, brightness=255):
        """Set warm white (automatically turns on bulb)"""
        cmd = [0x31, 0x00, 0x00, 0x00, brightness, 0x00, 0x0F, 0xF0]
        cmd.append(self.checksum(cmd))
        return self.send_command(cmd)

    def apply_brightness_to_rgb(self, r, g, b, brightness_percent):
        """Apply brightness percentage to RGB values"""
        scale = brightness_percent / 100.0
        return int(r * scale), int(g * scale), int(b * scale)

    def get_full_brightness_color(self, status):
        """Extract the full-brightness color from current status"""
        if status["warm_white"] > 0:
            return None  # Warm white mode

        # Find the maximum RGB value (this represents 100% of that color channel)
        max_val = max(status["red"], status["green"], status["blue"])

        if max_val == 0:
            return (255, 255, 255)  # Default to white if all values are 0

        # Scale all values back to full brightness
        scale = 255.0 / max_val
        r = min(255, int(status["red"] * scale))
        g = min(255, int(status["green"] * scale))
        b = min(255, int(status["blue"] * scale))

        return (r, g, b)

    def set_brightness_only(self, brightness_percent):
        """Change brightness while preserving current color"""
        status = self.query_status()

        if not status or not status["on"]:
            # If bulb is off or unreachable, turn on as white at requested brightness
            r, g, b = self.apply_brightness_to_rgb(255, 255, 255, brightness_percent)
            return self.set_rgb(r, g, b)

        if status["warm_white"] > 0:
            # Currently in warm white mode
            brightness_val = int((brightness_percent * 255) / 100)
            return self.set_warm_white(brightness_val)
        else:
            # Currently in RGB mode - preserve the color
            full_color = self.get_full_brightness_color(status)
            if full_color:
                r, g, b = self.apply_brightness_to_rgb(
                    full_color[0], full_color[1], full_color[2], brightness_percent
                )
                return self.set_rgb(r, g, b)
            else:
                # Fallback to white
                r, g, b = self.apply_brightness_to_rgb(
                    255, 255, 255, brightness_percent
                )
                return self.set_rgb(r, g, b)

    def set_color(self, color_hex):
        """Set color at full brightness"""
        if color_hex.upper() == "WW":
            return self.set_warm_white(255)
        else:
            r, g, b = self.hex_to_rgb(color_hex)
            return self.set_rgb(r, g, b)

    def set_color_with_brightness(self, color_hex, brightness_percent):
        """Set color with specific brightness in one command"""
        if color_hex.upper() == "WW":
            brightness_val = int((brightness_percent * 255) / 100)
            return self.set_warm_white(brightness_val)
        else:
            r, g, b = self.hex_to_rgb(color_hex)
            r, g, b = self.apply_brightness_to_rgb(r, g, b, brightness_percent)
            return self.set_rgb(r, g, b)

    def query_status(self):
        """Query actual bulb status"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(3)
                sock.connect((self.ip, self.port))
                query_cmd = [0x81, 0x8A, 0x8B, 0x96]
                sock.send(bytes(query_cmd))
                response = sock.recv(1024)

            if len(response) >= 14:
                return {
                    "on": response[2] == 0x23,
                    "red": response[6],
                    "green": response[7],
                    "blue": response[8],
                    "warm_white": response[9],
                }
        except:
            pass
        return None

    def hex_to_rgb(self, hex_color):
        """Convert hex to RGB tuple"""
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def get_target_bulbs(target):
    """Get list of bulb IPs for target"""
    if target in BULBS:
        return [(target, BULBS[target])]
    elif target in GROUPS:
        return [(name, BULBS[name]) for name in GROUPS[target] if name in BULBS]
    else:
        return []


def format_status(name, status):
    """Format status output consistently"""
    if not status:
        return f"{name} UNREACHABLE"

    if not status["on"]:
        return f"{name} OFF"

    if status["warm_white"] > 0:
        brightness_pct = int((status["warm_white"] * 100) / 255)
        return f"{name} warm white {brightness_pct}%"
    else:
        hex_color = (
            f"#{status['red']:02x}{status['green']:02x}{status['blue']:02x}".upper()
        )
        color_name = next(
            (name for name, hex_val in COLORS.items() if hex_val.upper() == hex_color),
            hex_color,
        )
        brightness_pct = int(
            (max(status["red"], status["green"], status["blue"]) * 100) / 255
        )
        return f"{name} {color_name} {brightness_pct}%"


def execute_command(target, command, value=None):
    """Execute a command on target bulb(s)"""
    bulbs = get_target_bulbs(target)
    if not bulbs:
        print(f"Unknown target: {target}")
        return

    for name, ip in bulbs:
        led = LEDController(ip)
        success = False

        if command == "on":
            success = led.power_on()
        elif command == "off":
            success = led.power_off()
        elif command == "toggle":
            status = led.query_status()
            if status and status["on"]:
                success = led.power_off()
            else:
                success = led.power_on()
        elif command == "color":
            success = led.set_color(value)
        elif command == "brightness":
            success = led.set_brightness_only(value)
        elif command == "color_brightness":
            if value and isinstance(value, (tuple, list)) and len(value) == 2:
                color, brightness = value
                success = led.set_color_with_brightness(color, brightness)
            else:
                print(f"Invalid color_brightness value: {value}")
                continue
        elif command == "status":
            status = led.query_status()
            print(format_status(name, status))
            continue

        if success:
            status = led.query_status()
            print(format_status(name, status))
        else:
            print(f"{name} FAILED")


def parse_args(args):
    """Parse command line arguments"""
    if not args:
        return None, None, None

    target = args[0]

    if len(args) == 1:
        return target, "toggle", None

    # Check for explicit commands first
    if args[1].lower() in ["on", "off", "status"]:
        return target, args[1].lower(), None

    # Parse remaining arguments
    color = None
    brightness = None

    for arg in args[1:]:
        if arg.isdigit():
            brightness = max(0, min(100, int(arg)))
        elif arg.startswith("#") and len(arg) == 7:
            color = arg
        elif arg.startswith("0x") and len(arg) == 8:
            # Handle 0x prefix hex colors
            color = "#" + arg[2:]
        elif len(arg) == 6 and all(c in "0123456789abcdefABCDEF" for c in arg):
            # Handle bare hex colors (no # or 0x prefix)
            color = "#" + arg
        elif arg.lower() in COLORS:
            color = COLORS[arg.lower()]
        else:
            print(f"Unknown argument: {arg}")
            return None, None, None

    # Determine command type
    if color and brightness is not None:
        return target, "color_brightness", (color, brightness)
    elif color:
        return target, "color", color
    elif brightness is not None:
        return target, "brightness", brightness
    else:
        return target, "toggle", None


def show_help():
    """Show usage information"""
    print("LED Bulb Control API")
    print("\nUsage:")
    print("  led_api.py <target>                  # Toggle on/off")
    print("  led_api.py <target> on/off           # Explicit on/off")
    print("  led_api.py <target> <color>          # Set color")
    print("  led_api.py <target> <color> <brightness> # Set color with brightness")
    print("  led_api.py <target> status           # Show current status")

    print("\nTargets:")
    print("  Individual bulbs:")
    for name, ip in BULBS.items():
        print(f"    {name:<12} {ip}")
    print("  Groups:")
    for name, bulbs in GROUPS.items():
        print(f"    {name:<12} {', '.join(bulbs)}")

    print("\nColors:")
    color_list = [name for name in COLORS.keys()]
    for i in range(0, len(color_list), 4):
        row = color_list[i : i + 4]
        print(f"  {' '.join(f'{c:<12}' for c in row)}")


def main():
    if len(sys.argv) < 2:
        show_help()
        return

    target, command, value = parse_args(sys.argv[1:])

    if not target or not command:
        show_help()
        return

    execute_command(target, command, value)


if __name__ == "__main__":
    main()

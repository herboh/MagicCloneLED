#!/usr/bin/env python3
"""
Elegant LED Bulb API
Usage:
  led_api.py lamp                    # Toggle on/off
  led_api.py lamp red                # Set color
  led_api.py lamp #FF0000            # Set hex color
  led_api.py lamp warmwhite          # Set warm white
  led_api.py lamp orange 90          # Set color + brightness
  led_api.py lamp 50                 # Set brightness only
"""

import socket
import sys

BULBS = {
    "lamp": "192.168.1.198",
    "downlamp": "192.168.1.105",
    "fireplace1": "192.168.1.165",
    "fireplace2": "192.168.1.161",
    # Add more bulbs as needed
}

# Color presets
COLORS = {
    "red": "#FF0000",
    "green": "#00FF00",
    "blue": "#0000FF",
    "orange": "#FFA500",
    "purple": "#800080",
    "yellow": "#FFFF00",
    "cyan": "#00FFFF",
    "magenta": "#FF00FF",
    "white": "#FFFFFF",
    "pink": "#FFC0CB",
    "lime": "#00FF00",
    "indigo": "#4B0082",
    "warmwhite": "WW",
    "warm": "WW",
}


class LEDController:
    def __init__(self, ip, port=5577):
        self.ip = ip
        self.port = port
        self.last_known_on = False  # Simple on/off tracking for toggle

    def query_status(self):
        """Query actual bulb status"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((self.ip, self.port))

            # Send status query: 0x81 0x8A 0x8B 0x96
            query_cmd = [0x81, 0x8A, 0x8B, 0x96]
            sock.send(bytes(query_cmd))

            # Read response
            response = sock.recv(1024)
            sock.close()

            if len(response) >= 14:
                # Parse response (simplified)
                power_state = response[2] == 0x23  # 0x23 = on, 0x24 = off
                red = response[6] if len(response) > 6 else 0
                green = response[7] if len(response) > 7 else 0
                blue = response[8] if len(response) > 8 else 0
                warm_white = response[9] if len(response) > 9 else 0

                return {
                    "on": power_state,
                    "red": red,
                    "green": green,
                    "blue": blue,
                    "warm_white": warm_white,
                }
        except:
            pass
        return None

    def send_command(self, data):
        """Send command to LED"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((self.ip, self.port))
            sock.send(bytes(data))
            sock.close()
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False

    def checksum(self, data):
        """Calculate checksum"""
        return sum(data) & 0xFF

    def power_on(self):
        """Turn on"""
        cmd = [0x71, 0x23, 0x0F]
        cmd.append(self.checksum(cmd))
        return self.send_command(cmd)

    def power_off(self):
        """Turn off"""
        cmd = [0x71, 0x24, 0x0F]
        cmd.append(self.checksum(cmd))
        return self.send_command(cmd)

    def set_rgb(self, red, green, blue, brightness=None):
        """Set RGB color with optional brightness"""
        if brightness is not None:
            red = int((red * brightness) / 255)
            green = int((green * brightness) / 255)
            blue = int((blue * brightness) / 255)

        cmd = [0x31, red, green, blue, 0x00, 0x00, 0xF0, 0x0F]
        cmd.append(self.checksum(cmd))
        return self.send_command(cmd)

    def set_warm_white(self, brightness=255):
        """Set warm white"""
        cmd = [0x31, 0x00, 0x00, 0x00, brightness, 0x00, 0x0F, 0xF0]
        cmd.append(self.checksum(cmd))
        return self.send_command(cmd)

    def hex_to_rgb(self, hex_color):
        """Convert hex to RGB tuple"""
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    def apply_command(self, color=None, brightness=None, toggle=False):
        """Apply a command with smart logic"""

        # Handle toggle
        if toggle:
            if self.last_known_on:
                success = self.power_off()
                self.last_known_on = False
                return success

        success = True
        if color or brightness is not None:
            if color == "WW":  # Warm white
                brightness = brightness or 255
                success = self.set_warm_white(brightness)
            else:
                if color:
                    if color.startswith("#"):
                        r, g, b = self.hex_to_rgb(color)
                    else:
                        r, g, b = self.hex_to_rgb(color)  # Should be resolved already
                else:
                    r, g, b = 255, 255, 255

                brightness = brightness or 255
                success = self.set_rgb(r, g, b, brightness)
        else:
            success = self.power_on()

        if success:
            self.last_known_on = True

        return success


def parse_args(args):
    """Parse command line arguments intelligently"""
    if len(args) < 1:
        return None, None, None, True  # Show help

    bulb_name = args[0]

    if len(args) == 1:
        # Just bulb name - toggle
        return bulb_name, None, None, False

    color = None
    brightness = None

    for arg in args[1:]:
        # Check if it's a number (brightness)
        if arg.isdigit():
            brightness = int(min(100, max(0, int(arg))))  # 0-100
            brightness = int((brightness * 255) / 100)  # Convert to 0-255

        # Check if it's a hex color
        elif arg.startswith("#") and len(arg) == 7:
            color = arg

        # Check if it's a color name
        elif arg.lower() in COLORS:
            color = COLORS[arg.lower()]

        else:
            print(f"Unknown argument: {arg}")
            return None, None, None, True

    return bulb_name, color, brightness, False


def show_help():
    """Show usage information"""
    print("LED Bulb Control API")
    print("\nUsage:")
    print("  led_api.py <bulb>                    # Toggle on/off")
    print("  led_api.py <bulb> <color>            # Set color")
    print("  led_api.py <bulb> <brightness>       # Set brightness (0-100)")
    print("  led_api.py <bulb> <color> <brightness>")
    print("\nBulbs:")
    for name, ip in BULBS.items():
        print(f"  {name:<10} {ip}")
    print("\nColors:")
    color_list = [name for name in COLORS.keys() if name != "warm"]
    for i in range(0, len(color_list), 4):
        row = color_list[i : i + 4]
        print(f"  {' '.join(f'{c:<12}' for c in row)}")
    print("\nExamples:")
    print("  led_api.py lamp                      # Toggle lamp")
    print("  led_api.py lamp red                  # Set to red")
    print("  led_api.py lamp #FF0000              # Set to red (hex)")
    print("  led_api.py lamp warmwhite            # Set to warm white")
    print("  led_api.py lamp orange 90            # Orange at 90% brightness")
    print("  led_api.py lamp 50                   # 50% brightness, keep color")


def main():
    bulb_name, color, brightness, show_help_flag = parse_args(sys.argv[1:])

    if show_help_flag:
        show_help()
        return

    if bulb_name not in BULBS:
        print(f"Unknown bulb: {bulb_name}")
        print(f"Available bulbs: {', '.join(BULBS.keys())}")
        return

    ip = BULBS[bulb_name]
    led = LEDController(ip)

    # Determine if this is a toggle operation
    toggle = color is None and brightness is None

    if led.apply_command(color=color, brightness=brightness, toggle=toggle):
        # Try to get actual status from bulb
        status = led.query_status()
        if status:
            status_parts = [bulb_name]
            if not status["on"]:
                status_parts.append("OFF")
            else:
                if status["warm_white"] > 0:
                    status_parts.append("warm white")
                    brightness_pct = int((status["warm_white"] * 100) / 255)
                else:
                    # Find closest color name or show hex
                    hex_color = f"#{status['red']:02x}{status['green']:02x}{status['blue']:02x}".upper()
                    color_name = None
                    for name, hex_val in COLORS.items():
                        if hex_val.upper() == hex_color:
                            color_name = name
                            break
                    status_parts.append(color_name or hex_color)
                    # Calculate brightness from RGB
                    brightness_pct = int(
                        (max(status["red"], status["green"], status["blue"]) * 100)
                        / 255
                    )

                status_parts.append(f"{brightness_pct}%")

            print(" ".join(status_parts))
        else:
            # Fallback to simple confirmation
            if toggle and not led.last_known_on:
                print(f"{bulb_name} OFF")
            else:
                print(f"{bulb_name} ON")
    else:
        print(f"Failed to control {bulb_name}")


if __name__ == "__main__":
    main()

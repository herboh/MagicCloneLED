#!/usr/bin/env python3
"""
Simple Magic Home LED Bulb Controller
Usage: python led_control.py 192.168.1.105 ff0000 80
       (IP, hex color, brightness 0-255)
"""

import socket
import sys
import time


class MagicHomeLED:
    def __init__(self, ip, port=5577):
        self.ip = ip
        self.port = port
        self.sock = None

    def connect(self):
        """Connect to the LED bulb"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
            self.sock.connect((self.ip, self.port))
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def disconnect(self):
        """Close connection"""
        if self.sock:
            self.sock.close()
            self.sock = None

    def send_command(self, data):
        """Send raw command to bulb"""
        if not self.sock:
            if not self.connect():
                return False

        try:
            self.sock.send(bytes(data))
            return True
        except Exception as e:
            print(f"Send failed: {e}")
            return False

    def checksum(self, data):
        """Calculate checksum for command"""
        return sum(data) & 0xFF

    def power_on(self):
        """Turn bulb on"""
        cmd = [0x71, 0x23, 0x0F]
        cmd.append(self.checksum(cmd))
        return self.send_command(cmd)

    def power_off(self):
        """Turn bulb off"""
        cmd = [0x71, 0x24, 0x0F]
        cmd.append(self.checksum(cmd))
        return self.send_command(cmd)

    def set_color(self, red, green, blue, warm_white=0, brightness=255):
        """
        Set RGB color and brightness
        red, green, blue: 0-255
        warm_white: 0-255 (if supported)
        brightness: 0-255 (applied to RGB)
        """
        # Apply brightness scaling to RGB
        red = int((red * brightness) / 255)
        green = int((green * brightness) / 255)
        blue = int((blue * brightness) / 255)

        # Command format: 0x31 R G B WW CW 0xF0 0x0F CHECKSUM
        cmd = [0x31, red, green, blue, warm_white, 0x00, 0xF0, 0x0F]
        cmd.append(self.checksum(cmd))

        return self.send_command(cmd)

    def set_hex_color(self, hex_color, brightness=255):
        """
        Set color using hex string (e.g., 'ff0000' for red)
        brightness: 0-255
        """
        # Remove '#' if present
        hex_color = hex_color.lstrip("#")

        # Parse hex color
        if len(hex_color) != 6:
            raise ValueError("Hex color must be 6 characters (RRGGBB)")

        red = int(hex_color[0:2], 16)
        green = int(hex_color[2:4], 16)
        blue = int(hex_color[4:6], 16)

        return self.set_color(red, green, blue, brightness=brightness)


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python led_control.py <IP> on")
        print("  python led_control.py <IP> off")
        print("  python led_control.py <IP> <hex_color> [brightness]")
        print("Examples:")
        print("  python led_control.py 192.168.1.105 on")
        print("  python led_control.py 192.168.1.105 ff0000 128")
        print("  python led_control.py 192.168.1.105 00ff00")
        return

    ip = sys.argv[1]
    led = MagicHomeLED(ip)

    if not led.connect():
        print("Failed to connect to LED bulb")
        return

    if len(sys.argv) == 3:
        command = sys.argv[2].lower()

        if command == "on":
            if led.power_on():
                print("Bulb turned on")
            else:
                print("Failed to turn on bulb")
        elif command == "off":
            if led.power_off():
                print("Bulb turned off")
            else:
                print("Failed to turn off bulb")
        else:
            # Treat as hex color with full brightness
            try:
                if led.set_hex_color(command, 255):
                    print(f"Color set to #{command}")
                else:
                    print("Failed to set color")
            except ValueError as e:
                print(f"Error: {e}")

    elif len(sys.argv) == 4:
        hex_color = sys.argv[2]
        brightness = int(sys.argv[3])

        try:
            if led.set_hex_color(hex_color, brightness):
                print(f"Color set to #{hex_color} with brightness {brightness}")
            else:
                print("Failed to set color")
        except ValueError as e:
            print(f"Error: {e}")

    led.disconnect()


if __name__ == "__main__":
    main()

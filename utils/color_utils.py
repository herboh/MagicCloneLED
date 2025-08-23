"""
Fast HSV/RGB color conversion utilities
Optimized for LED control applications
"""


def hsv_to_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    """
    Convert HSV to RGB values
    h: 0-360 (hue)
    s: 0-100 (saturation percentage)
    v: 0-100 (value/brightness percentage)
    Returns: (r, g, b) as 0-255 integers
    """
    # Normalize inputs
    h = h % 360
    s = max(0, min(100, s)) / 100.0
    v = max(0, min(100, v)) / 100.0

    if s == 0:
        # Grayscale
        val = int(v * 255)
        return (val, val, val)

    # Convert hue to 0-6 range
    h_sector = h / 60.0
    sector = int(h_sector)
    f = h_sector - sector

    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))

    if sector == 0:
        r, g, b = v, t, p
    elif sector == 1:
        r, g, b = q, v, p
    elif sector == 2:
        r, g, b = p, v, t
    elif sector == 3:
        r, g, b = p, q, v
    elif sector == 4:
        r, g, b = t, p, v
    else:  # sector == 5
        r, g, b = v, p, q

    return (int(r * 255), int(g * 255), int(b * 255))


def rgb_to_hsv(r: int, g: int, b: int) -> tuple[float, float, float]:
    """
    Convert RGB to HSV values
    r, g, b: 0-255 integers
    Returns: (h, s, v) where h=0-360, s=0-100, v=0-100
    """
    # Normalize to 0-1
    r_norm = r / 255.0
    g_norm = g / 255.0
    b_norm = b / 255.0

    max_val = max(r_norm, g_norm, b_norm)
    min_val = min(r_norm, g_norm, b_norm)
    delta = max_val - min_val

    # Value (brightness)
    v = max_val * 100

    # Saturation
    if max_val == 0:
        s = 0
    else:
        s = (delta / max_val) * 100

    # Hue
    if delta == 0:
        h = 0
    elif max_val == r_norm:
        h = 60 * (((g_norm - b_norm) / delta) % 6)
    elif max_val == g_norm:
        h = 60 * ((b_norm - r_norm) / delta + 2)
    else:  # max_val == b_norm
        h = 60 * ((r_norm - g_norm) / delta + 4)

    return (h, s, v)


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip("#")
    return (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB to hex string"""
    return f"#{r:02x}{g:02x}{b:02x}".upper()


def hsv_to_hex(h: float, s: float, v: float) -> str:
    """Convert HSV directly to hex"""
    r, g, b = hsv_to_rgb(h, s, v)
    return rgb_to_hex(r, g, b)


def hex_to_hsv(hex_color: str) -> tuple[float, float, float]:
    """Convert hex directly to HSV"""
    r, g, b = hex_to_rgb(hex_color)
    return rgb_to_hsv(r, g, b)


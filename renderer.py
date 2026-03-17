"""Render a 64x64 pixel weather image for the iDotMatrix display."""

from PIL import Image, ImageDraw

from weather import WeatherData

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
SKY_DAY = (40, 40, 80)
WHITE = (255, 255, 255)
YELLOW = (255, 220, 50)
ORANGE = (255, 160, 50)
GRAY = (180, 180, 190)
DARK_GRAY = (120, 120, 130)
BLUE = (80, 160, 255)
DARK_BLUE = (40, 80, 200)
GREEN_LIGHT = (80, 200, 80)
GREEN_DARK = (40, 160, 50)
PINK = (255, 120, 180)
RED = (220, 60, 60)
SNOW_WHITE = (220, 230, 255)
LIGHTNING = (255, 255, 100)
FOG_COLOR = (160, 170, 180)

# ---------------------------------------------------------------------------
# 5x7 bitmap font — each glyph is a list of 7 rows, each row is 5 bits wide
# (MSB-left). Only the characters we need.
# ---------------------------------------------------------------------------
FONT_5x7 = {
    "0": [0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E],
    "1": [0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E],
    "2": [0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F],
    "3": [0x0E, 0x11, 0x01, 0x06, 0x01, 0x11, 0x0E],
    "4": [0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02],
    "5": [0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E],
    "6": [0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E],
    "7": [0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08],
    "8": [0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E],
    "9": [0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C],
    "-": [0x00, 0x00, 0x00, 0x0E, 0x00, 0x00, 0x00],
    " ": [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
}

# 3x5 compact font for small labels
FONT_3x5 = {
    "0": [0x7, 0x5, 0x5, 0x5, 0x7],
    "1": [0x2, 0x6, 0x2, 0x2, 0x7],
    "2": [0x7, 0x1, 0x7, 0x4, 0x7],
    "3": [0x7, 0x1, 0x7, 0x1, 0x7],
    "4": [0x5, 0x5, 0x7, 0x1, 0x1],
    "5": [0x7, 0x4, 0x7, 0x1, 0x7],
    "6": [0x7, 0x4, 0x7, 0x5, 0x7],
    "7": [0x7, 0x1, 0x2, 0x4, 0x4],
    "8": [0x7, 0x5, 0x7, 0x5, 0x7],
    "9": [0x7, 0x5, 0x7, 0x1, 0x7],
    "-": [0x0, 0x0, 0x7, 0x0, 0x0],
    "%": [0x5, 0x1, 0x2, 0x4, 0x5],
    " ": [0x0, 0x0, 0x0, 0x0, 0x0],
    "H": [0x5, 0x5, 0x7, 0x5, 0x5],
    "i": [0x2, 0x0, 0x2, 0x2, 0x2],
    "R": [0x6, 0x5, 0x6, 0x5, 0x5],
    "a": [0x0, 0x7, 0x5, 0x7, 0x5],
    "n": [0x0, 0x6, 0x5, 0x5, 0x5],
    "M": [0x5, 0x7, 0x5, 0x5, 0x5],
    "x": [0x0, 0x5, 0x2, 0x5, 0x5],
    ":": [0x0, 0x2, 0x0, 0x2, 0x0],
}


def _draw_char_5x7(draw: ImageDraw.ImageDraw, ch: str, x: int, y: int, color):
    glyph = FONT_5x7.get(ch)
    if glyph is None:
        return
    for row_i, row_bits in enumerate(glyph):
        for col_i in range(5):
            if row_bits & (0x10 >> col_i):
                draw.point((x + col_i, y + row_i), fill=color)


def _draw_char_3x5(draw: ImageDraw.ImageDraw, ch: str, x: int, y: int, color):
    glyph = FONT_3x5.get(ch)
    if glyph is None:
        return
    for row_i, row_bits in enumerate(glyph):
        for col_i in range(3):
            if row_bits & (0x4 >> col_i):
                draw.point((x + col_i, y + row_i), fill=color)


def _draw_text_5x7(draw, text: str, x: int, y: int, color):
    cx = x
    for ch in text:
        _draw_char_5x7(draw, ch, cx, y, color)
        cx += 6


def _draw_text_3x5(draw, text: str, x: int, y: int, color):
    cx = x
    for ch in text:
        _draw_char_3x5(draw, ch, cx, y, color)
        cx += 4


def _text_width_5x7(text: str) -> int:
    return max(0, len(text) * 6 - 1)


def _text_width_3x5(text: str) -> int:
    return max(0, len(text) * 4 - 1)


# ---------------------------------------------------------------------------
# Degree symbol — a tiny 2x2 circle drawn at the top-right of the temperature
# ---------------------------------------------------------------------------
def _draw_degree(draw, x: int, y: int, color):
    draw.point((x, y), fill=color)
    draw.point((x + 1, y), fill=color)
    draw.point((x, y + 1), fill=color)
    draw.point((x + 1, y + 1), fill=color)


# ---------------------------------------------------------------------------
# Weather icons — 24x24 pixel art, drawn onto the image at (ox, oy)
# ---------------------------------------------------------------------------

def _draw_sun(draw, ox: int, oy: int):
    # Rays
    for i in range(3):
        draw.point((ox + 11 + i, oy + 2), fill=YELLOW)
        draw.point((ox + 11 + i, oy + 21), fill=YELLOW)
        draw.point((ox + 2, oy + 11 + i), fill=YELLOW)
        draw.point((ox + 21, oy + 11 + i), fill=YELLOW)

    # Diagonal rays
    for i in range(2):
        draw.point((ox + 5 + i, oy + 5 + i), fill=YELLOW)
        draw.point((ox + 17 + i, oy + 5 + i), fill=YELLOW)
        draw.point((ox + 5 + i, oy + 17 + i), fill=YELLOW)
        draw.point((ox + 17 + i, oy + 17 + i), fill=YELLOW)

    # Sun body
    draw.ellipse(
        [ox + 7, oy + 7, ox + 17, oy + 17],
        fill=YELLOW,
        outline=ORANGE,
    )


def _draw_cloud(draw, ox: int, oy: int, color=GRAY, outline=DARK_GRAY):
    draw.ellipse([ox + 4, oy + 8, ox + 14, oy + 18], fill=color, outline=outline)
    draw.ellipse([ox + 9, oy + 5, ox + 19, oy + 15], fill=color, outline=outline)
    draw.ellipse([ox + 13, oy + 9, ox + 21, oy + 17], fill=color, outline=outline)
    draw.rectangle([ox + 6, oy + 13, ox + 19, oy + 17], fill=color)


def _draw_rain(draw, ox: int, oy: int):
    _draw_cloud(draw, ox, oy)
    drops = [(ox + 7, oy + 19), (ox + 12, oy + 20), (ox + 17, oy + 19)]
    for dx, dy in drops:
        draw.line([(dx, dy), (dx, dy + 3)], fill=BLUE, width=1)


def _draw_snow(draw, ox: int, oy: int):
    _draw_cloud(draw, ox, oy)
    flakes = [
        (ox + 7, oy + 19), (ox + 10, oy + 21), (ox + 14, oy + 19),
        (ox + 17, oy + 21), (ox + 9, oy + 23), (ox + 15, oy + 23),
    ]
    for fx, fy in flakes:
        if 0 <= fy < 64:
            draw.point((fx, fy), fill=SNOW_WHITE)


def _draw_thunderstorm(draw, ox: int, oy: int):
    _draw_cloud(draw, ox, oy, color=DARK_GRAY, outline=GRAY)
    bolt = [
        (ox + 13, oy + 16), (ox + 11, oy + 19),
        (ox + 14, oy + 19), (ox + 10, oy + 23),
    ]
    draw.line(bolt, fill=LIGHTNING, width=1)


def _draw_fog(draw, ox: int, oy: int):
    for i, y_off in enumerate([8, 11, 14, 17]):
        x_start = ox + 4 + (i % 2) * 2
        draw.line([(x_start, oy + y_off), (x_start + 14, oy + y_off)], fill=FOG_COLOR)


ICON_DISPATCH = {
    "clear": _draw_sun,
    "cloudy": _draw_cloud,
    "rain": _draw_rain,
    "snow": _draw_snow,
    "thunderstorm": _draw_thunderstorm,
    "fog": _draw_fog,
}


def _condition_from_code(code: int) -> str:
    if code <= 1:
        return "clear"
    if code <= 3:
        return "cloudy"
    if code <= 48:
        return "fog"
    if code <= 67:
        return "rain"
    if code <= 77:
        return "snow"
    if code <= 82:
        return "rain"
    if code <= 99:
        return "thunderstorm"
    return "cloudy"


# ---------------------------------------------------------------------------
# Decorative pixel-art grass & flowers along the bottom
# ---------------------------------------------------------------------------

def _draw_ground(draw):
    for x in range(64):
        draw.point((x, 59), fill=GREEN_DARK)
        draw.point((x, 60), fill=GREEN_DARK)
        for y in range(61, 64):
            draw.point((x, y), fill=(50, 100, 40))

    # Grass blades
    blades = [3, 8, 14, 19, 25, 31, 38, 44, 50, 55, 60]
    for bx in blades:
        draw.point((bx, 58), fill=GREEN_LIGHT)
        draw.point((bx + 1, 57), fill=GREEN_LIGHT)

    # Tiny flowers
    flowers = [
        (6, 57, PINK), (22, 56, YELLOW), (35, 57, RED),
        (48, 56, PINK), (58, 57, YELLOW),
    ]
    for fx, fy, fc in flowers:
        draw.point((fx, fy), fill=fc)
        draw.point((fx - 1, fy), fill=fc)
        draw.point((fx + 1, fy), fill=fc)
        draw.point((fx, fy - 1), fill=fc)
        draw.point((fx, fy + 1), fill=fc)
        draw.point((fx, fy + 1), fill=GREEN_DARK)
        draw.point((fx, fy + 2), fill=GREEN_DARK)


# ---------------------------------------------------------------------------
# Public render function
# ---------------------------------------------------------------------------

def render_weather(data: WeatherData, output_path: str) -> str:
    img = Image.new("RGB", (64, 64), SKY_DAY)
    draw = ImageDraw.Draw(img)

    # -- weather icon (centered, 24x24 at top) --
    condition = _condition_from_code(data.weather_code)
    icon_fn = ICON_DISPATCH.get(condition, _draw_cloud)
    icon_ox = (64 - 24) // 2
    icon_fn(draw, icon_ox, -2)

    # -- current temperature (large, centered) --
    temp_str = str(int(round(data.current_temp)))
    tw = _text_width_5x7(temp_str)
    total_w = tw + 4
    tx = (64 - total_w) // 2
    ty = 22
    _draw_text_5x7(draw, temp_str, tx, ty, WHITE)
    _draw_degree(draw, tx + tw + 2, ty, WHITE)

    # -- Max: max temp (small, left side) --
    max_label = "Max:"
    max_val = str(int(round(data.max_temp)))
    lx = 2
    ly = 38
    _draw_text_3x5(draw, max_label, lx, ly, ORANGE)
    val_x = lx + _text_width_3x5(max_label) + 3
    _draw_text_3x5(draw, max_val, val_x, ly, WHITE)
    _draw_degree(draw, val_x + _text_width_3x5(max_val) + 1, ly, WHITE)

    # -- Rain: probability (small, left side, below Max) --
    rain_label = "Rain:"
    rain_val = f"{data.max_rain_probability}%"
    ry = 46
    _draw_text_3x5(draw, rain_label, lx, ry, BLUE)
    rv_x = lx + _text_width_3x5(rain_label) + 3
    _draw_text_3x5(draw, rain_val, rv_x, ry, WHITE)

    # -- decorative ground --
    _draw_ground(draw)

    img.save(output_path, format="PNG")
    return output_path

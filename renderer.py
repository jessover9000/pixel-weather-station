"""Render animated 64x64 Ghibli-style pixel art weather scenes.

Each weather condition has a dedicated scene painter that returns multiple
frames.  A semi-transparent overlay bar at the bottom shows current temp,
max temp, and rain probability.
"""

import random
from typing import List, Tuple

from PIL import Image, ImageDraw

from weather import WeatherData

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
Color = Tuple[int, int, int]


def _lerp_color(a: Color, b: Color, t: float) -> Color:
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def _gradient(draw: ImageDraw.ImageDraw, top: Color, bot: Color, y0: int, y1: int):
    for y in range(y0, y1):
        t = (y - y0) / max(1, y1 - y0 - 1)
        c = _lerp_color(top, bot, t)
        draw.line([(0, y), (63, y)], fill=c)


def _px2(draw: ImageDraw.ImageDraw, x: int, y: int, color: Color):
    """Draw a 2x2 pixel block (for double-size pixel art characters)."""
    draw.rectangle([x, y, x + 1, y + 1], fill=color)


def _blend(base: Color, overlay: Color, alpha: float) -> Color:
    return (
        int(base[0] * (1 - alpha) + overlay[0] * alpha),
        int(base[1] * (1 - alpha) + overlay[1] * alpha),
        int(base[2] * (1 - alpha) + overlay[2] * alpha),
    )


# ---------------------------------------------------------------------------
# 3x5 compact bitmap font
# ---------------------------------------------------------------------------
FONT = {
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
    "M": [0x5, 0x7, 0x5, 0x5, 0x5],
    "a": [0x0, 0x7, 0x5, 0x7, 0x5],
    "x": [0x0, 0x5, 0x2, 0x5, 0x5],
    "R": [0x6, 0x5, 0x6, 0x5, 0x5],
    "n": [0x0, 0x6, 0x5, 0x5, 0x5],
    "i": [0x2, 0x0, 0x2, 0x2, 0x2],
    ":": [0x0, 0x2, 0x0, 0x2, 0x0],
    "C": [0x7, 0x4, 0x4, 0x4, 0x7],
}


def _draw_char(draw: ImageDraw.ImageDraw, ch: str, x: int, y: int, color: Color):
    glyph = FONT.get(ch)
    if glyph is None:
        return
    for ri, bits in enumerate(glyph):
        for ci in range(3):
            if bits & (0x4 >> ci):
                draw.point((x + ci, y + ri), fill=color)


def _draw_text(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, color: Color):
    cx = x
    for ch in text:
        _draw_char(draw, ch, cx, y, color)
        cx += 4


def _text_width(text: str) -> int:
    return max(0, len(text) * 4 - 1)


def _draw_degree(draw: ImageDraw.ImageDraw, x: int, y: int, color: Color):
    draw.point((x, y), fill=color)
    draw.point((x + 1, y), fill=color)
    draw.point((x, y + 1), fill=color)
    draw.point((x + 1, y + 1), fill=color)


# ---------------------------------------------------------------------------
# Overlay bar (bottom of display)
# ---------------------------------------------------------------------------
OVERLAY_Y = 52
OVERLAY_H = 12
OVERLAY_BG = (30, 30, 40)
OVERLAY_ALPHA = 0.7
WHITE = (255, 255, 255)
WARM = (255, 200, 100)
COOL = (130, 200, 255)


def _apply_overlay(img: Image.Image, data: WeatherData) -> Image.Image:
    """Draw a semi-transparent info bar on the bottom 12 rows."""
    img = img.copy()
    px = img.load()

    for y in range(OVERLAY_Y, 64):
        for x in range(64):
            base = px[x, y]
            px[x, y] = _blend(base, OVERLAY_BG, OVERLAY_ALPHA)

    draw = ImageDraw.Draw(img)

    temp_str = f"{int(round(data.current_temp))}"
    tw = _text_width(temp_str)
    _draw_text(draw, temp_str, 2, OVERLAY_Y + 1, WHITE)
    _draw_degree(draw, 2 + tw + 1, OVERLAY_Y + 1, WHITE)
    _draw_char(draw, "C", 2 + tw + 4, OVERLAY_Y + 1, WHITE)

    max_str = f"Max:{int(round(data.max_temp))}"
    mw = _text_width(max_str)
    _draw_text(draw, max_str, 36, OVERLAY_Y + 1, WARM)
    _draw_degree(draw, 36 + mw + 1, OVERLAY_Y + 1, WARM)

    rain_str = f"Rain:{data.max_rain_probability}%"
    rain_x = 64 - _text_width(rain_str) - 2
    _draw_text(draw, rain_str, rain_x, OVERLAY_Y + 7, COOL)

    return img


# ---------------------------------------------------------------------------
# Scene: SUNNY — Ghibli meadow with big tree, butterflies
# ---------------------------------------------------------------------------

def _scene_sunny(num_frames: int = 4) -> List[Image.Image]:
    frames = []
    sky_top = (110, 180, 240)
    sky_bot = (170, 215, 255)
    sun_color = (255, 230, 80)
    sun_rim = (255, 190, 50)
    grass_light = (100, 200, 80)
    grass_mid = (70, 170, 60)
    grass_dark = (50, 140, 45)
    trunk = (100, 70, 40)
    canopy_light = (60, 170, 60)
    canopy_dark = (40, 130, 45)
    hill_far = (130, 195, 120)

    for f in range(num_frames):
        img = Image.new("RGB", (64, 64))
        draw = ImageDraw.Draw(img)

        _gradient(draw, sky_top, sky_bot, 0, 35)

        # sun
        draw.ellipse([48, 3, 59, 14], fill=sun_color, outline=sun_rim)
        rays = [(53, 0), (53, 1), (61, 7), (62, 8), (47, 8), (46, 7),
                (58, 2), (59, 3), (48, 2), (47, 3), (60, 13), (58, 15)]
        for rx, ry in rays:
            if 0 <= rx < 64 and 0 <= ry < 64:
                draw.point((rx, ry), fill=sun_color)

        # distant clouds (drift with frame)
        cx = (10 + f * 2) % 30
        draw.ellipse([cx, 8, cx + 14, 14], fill=(230, 235, 245))
        draw.ellipse([cx + 6, 5, cx + 18, 13], fill=(240, 242, 250))
        draw.ellipse([cx + 12, 8, cx + 22, 14], fill=(232, 236, 248))

        # far hills
        for x in range(64):
            hill_y = 32 + int(3 * ((x - 32) / 40) ** 2)
            for y in range(hill_y, 38):
                draw.point((x, y), fill=hill_far)

        # ground
        _gradient(draw, grass_light, grass_dark, 35, 52)

        # big tree trunk (right of center)
        for y in range(22, 45):
            w = 3 if y < 35 else 4
            for x in range(38 - w // 2, 38 + w // 2 + 1):
                draw.point((x, y), fill=trunk)
        # roots
        for dx in [-3, -2, 3, 4]:
            draw.point((38 + dx, 44), fill=trunk)
            draw.point((38 + dx, 45), fill=trunk)

        # canopy
        draw.ellipse([26, 12, 50, 30], fill=canopy_dark)
        draw.ellipse([28, 10, 48, 26], fill=canopy_light)
        draw.ellipse([24, 16, 38, 28], fill=canopy_dark)
        draw.ellipse([40, 14, 52, 26], fill=canopy_light)

        # grass tufts
        tufts = [2, 8, 15, 22, 50, 56, 61]
        for tx in tufts:
            offset = (f + tx) % 2
            draw.point((tx, 36 + offset), fill=grass_light)
            draw.point((tx + 1, 35 + offset), fill=grass_light)

        # tiny flowers
        flowers = [(5, 42, (255, 120, 180)), (12, 40, (255, 220, 80)),
                   (20, 43, (255, 100, 100)), (52, 41, (255, 180, 220)),
                   (58, 39, (255, 255, 130)), (48, 44, (200, 130, 255))]
        for fx, fy, fc in flowers:
            sway = (f + fx) % 3 - 1
            draw.point((fx + sway, fy), fill=fc)
            draw.point((fx + sway, fy - 1), fill=fc)
            draw.point((fx + sway + 1, fy), fill=fc)
            draw.point((fx + sway - 1, fy), fill=fc)

        # butterflies
        bflies = [(10 + f * 4, 20 - f), (55 - f * 3, 18 + f)]
        for bx, by in bflies:
            bx, by = bx % 60 + 2, max(8, min(by % 30, 34))
            draw.point((bx, by), fill=(255, 255, 200))
            draw.point((bx - 1, by - 1), fill=(255, 200, 100))
            draw.point((bx + 1, by - 1), fill=(255, 200, 100))

        # Totoro standing under the tree — detailed pixel art (~10x16)
        tx, ty = 4, 30
        t_body = (130, 140, 145)
        t_light = (155, 165, 170)
        t_dark = (90, 100, 105)
        t_belly = (215, 220, 205)
        t_chev = (80, 90, 95)
        t_eye_w = (235, 240, 245)
        t_pupil = (25, 25, 30)
        t_nose = (75, 80, 85)
        t_claw = (60, 55, 50)
        t_hi = (170, 180, 185)
        # pointed ears with inner highlight
        draw.point((tx + 1, ty), fill=t_body)
        draw.point((tx + 8, ty), fill=t_body)
        draw.point((tx + 1, ty + 1), fill=t_body)
        draw.point((tx + 2, ty + 1), fill=t_light)
        draw.point((tx + 7, ty + 1), fill=t_light)
        draw.point((tx + 8, ty + 1), fill=t_body)
        # rounded head
        for dx in range(2, 8):
            draw.point((tx + dx, ty + 2), fill=t_body)
        for dx in range(1, 9):
            draw.point((tx + dx, ty + 3), fill=t_body)
        for dx in range(0, 10):
            draw.point((tx + dx, ty + 4), fill=t_body)
        # eyes with pupils and highlights
        draw.point((tx + 2, ty + 4), fill=t_eye_w)
        draw.point((tx + 3, ty + 4), fill=t_pupil)
        draw.point((tx + 6, ty + 4), fill=t_pupil)
        draw.point((tx + 7, ty + 4), fill=t_eye_w)
        draw.point((tx + 2, ty + 3), fill=(255, 255, 255))
        draw.point((tx + 7, ty + 3), fill=(255, 255, 255))
        # nose and mouth row
        for dx in range(0, 10):
            draw.point((tx + dx, ty + 5), fill=t_body)
        draw.point((tx + 4, ty + 5), fill=t_nose)
        draw.point((tx + 5, ty + 5), fill=t_nose)
        for dx in range(1, 9):
            draw.point((tx + dx, ty + 6), fill=t_body)
        draw.point((tx + 3, ty + 6), fill=t_dark)
        draw.point((tx + 6, ty + 6), fill=t_dark)
        # body with shaded sides
        for dy in range(7, 13):
            for dx in range(0, 10):
                draw.point((tx + dx, ty + dy), fill=t_body)
            draw.point((tx, ty + dy), fill=t_dark)
            draw.point((tx + 9, ty + dy), fill=t_dark)
        # shoulder highlights
        draw.point((tx + 1, ty + 7), fill=t_hi)
        draw.point((tx + 2, ty + 7), fill=t_hi)
        # belly patch
        for dy in range(8, 12):
            for dx in range(2, 8):
                draw.point((tx + dx, ty + dy), fill=t_belly)
        # V-shaped chevron rows
        draw.point((tx + 4, ty + 8), fill=t_chev)
        draw.point((tx + 5, ty + 8), fill=t_chev)
        draw.point((tx + 3, ty + 9), fill=t_chev)
        draw.point((tx + 6, ty + 9), fill=t_chev)
        draw.point((tx + 4, ty + 10), fill=t_chev)
        draw.point((tx + 5, ty + 10), fill=t_chev)
        draw.point((tx + 3, ty + 11), fill=t_chev)
        draw.point((tx + 6, ty + 11), fill=t_chev)
        # lower body taper
        for dx in range(1, 9):
            draw.point((tx + dx, ty + 13), fill=t_body)
        # feet with claws
        for dx in [1, 2, 3]:
            draw.point((tx + dx, ty + 14), fill=t_body)
        for dx in [6, 7, 8]:
            draw.point((tx + dx, ty + 14), fill=t_body)
        draw.point((tx + 1, ty + 15), fill=t_claw)
        draw.point((tx + 3, ty + 15), fill=t_claw)
        draw.point((tx + 6, ty + 15), fill=t_claw)
        draw.point((tx + 8, ty + 15), fill=t_claw)
        # leaf on head (wobbles per frame)
        lx = tx + 4 + (f % 2)
        draw.point((lx, ty - 1), fill=(50, 160, 50))
        draw.point((lx + 1, ty - 1), fill=(60, 180, 60))
        draw.point((lx + 2, ty - 1), fill=(50, 160, 50))
        draw.point((lx + 1, ty - 2), fill=(60, 180, 60))
        draw.point((lx + 1, ty - 3), fill=(40, 130, 40))

        frames.append(img)
    return frames


# ---------------------------------------------------------------------------
# Scene: CLOUDY — Overcast rolling hills, drifting clouds
# ---------------------------------------------------------------------------

def _scene_cloudy(num_frames: int = 4) -> List[Image.Image]:
    frames = []
    sky_top = (140, 155, 175)
    sky_bot = (175, 185, 200)
    cloud_light = (210, 215, 225)
    cloud_mid = (190, 195, 210)
    hill1 = (100, 160, 90)
    hill2 = (80, 140, 70)
    grass = (85, 150, 75)

    for f in range(num_frames):
        img = Image.new("RGB", (64, 64))
        draw = ImageDraw.Draw(img)

        _gradient(draw, sky_top, sky_bot, 0, 35)

        # cloud layers drifting
        drift = f * 3
        for cy, cr, cc in [(8, 9, cloud_light), (12, 7, cloud_mid), (6, 8, cloud_light)]:
            cx = (drift + cy * 3) % 70 - 10
            draw.ellipse([cx, cy, cx + cr * 3, cy + cr], fill=cc)
            draw.ellipse([cx + cr, cy - 3, cx + cr * 4, cy + cr - 2], fill=cc)
            draw.ellipse([cx + cr * 2, cy, cx + cr * 4 + 4, cy + cr + 1], fill=cc)

        # rolling hills
        for x in range(64):
            h1 = 34 + int(4 * ((x - 20) / 50) ** 2)
            for y in range(h1, 40):
                draw.point((x, y), fill=hill1)
            h2 = 38 + int(3 * ((x - 45) / 40) ** 2)
            for y in range(h2, 52):
                draw.point((x, y), fill=hill2)

        _gradient(draw, grass, (60, 120, 55), 42, 52)

        # wind lines
        wind_offset = f * 5
        for wy in [25, 30, 22]:
            wx = (wind_offset + wy * 2) % 50
            draw.line([(wx, wy), (wx + 8, wy)], fill=(160, 170, 185))

        # small path
        for y in range(43, 52):
            pw = 2 + (y - 43) // 3
            px = 30 + (y - 43)
            draw.line([(px, y), (px + pw, y)], fill=(150, 140, 110))

        # Catbus running along the hilltop — detailed pixel art (~20x10)
        cat_body = (220, 170, 60)
        cat_lt = (240, 195, 85)
        cat_dk = (170, 120, 35)
        cat_fur = (200, 155, 50)
        eye_glow = (255, 240, 100)
        eye_pupil = (30, 30, 30)
        teeth_c = (255, 255, 250)
        grin_c = (240, 230, 220)
        window_c = (255, 220, 130)
        cx = (50 - f * 6) % 44 + 2
        cy = 30
        # pointed ears with inner color
        draw.point((cx, cy - 2), fill=cat_body)
        draw.point((cx + 4, cy - 2), fill=cat_body)
        draw.point((cx, cy - 1), fill=cat_body)
        draw.point((cx + 1, cy - 1), fill=cat_lt)
        draw.point((cx + 3, cy - 1), fill=cat_lt)
        draw.point((cx + 4, cy - 1), fill=cat_body)
        # head (5 wide)
        for dx in range(5):
            draw.point((cx + dx, cy), fill=cat_body)
            draw.point((cx + dx, cy + 1), fill=cat_body)
        # large glowing eyes with pupils
        draw.point((cx + 1, cy), fill=eye_glow)
        draw.point((cx + 3, cy), fill=eye_glow)
        draw.point((cx + 1, cy + 1), fill=eye_pupil)
        draw.point((cx + 3, cy + 1), fill=eye_pupil)
        # nose between eyes
        draw.point((cx + 2, cy + 1), fill=cat_dk)
        # wide grin with teeth
        for dx in range(5):
            draw.point((cx + dx, cy + 2), fill=cat_body)
        draw.point((cx + 1, cy + 2), fill=grin_c)
        draw.point((cx + 2, cy + 2), fill=teeth_c)
        draw.point((cx + 3, cy + 2), fill=grin_c)
        # whiskers
        draw.point((cx - 1, cy + 1), fill=cat_lt)
        draw.point((cx + 5, cy + 1), fill=cat_lt)
        # long bus body (columns 5-17)
        for dx in range(5, 18):
            draw.point((cx + dx, cy - 1), fill=cat_lt)
            draw.point((cx + dx, cy), fill=cat_body)
            draw.point((cx + dx, cy + 1), fill=cat_body)
            draw.point((cx + dx, cy + 2), fill=cat_fur)
        # dark stripes on body
        for sx in [7, 10, 13, 16]:
            draw.point((cx + sx, cy), fill=cat_dk)
            draw.point((cx + sx, cy + 1), fill=cat_dk)
        # glowing windows between stripes
        for wx in [8, 11, 14]:
            draw.point((cx + wx, cy), fill=window_c)
            draw.point((cx + wx + 1, cy), fill=window_c)
        # fluffy tail curling up
        draw.point((cx + 18, cy), fill=cat_body)
        draw.point((cx + 18, cy - 1), fill=cat_body)
        draw.point((cx + 19, cy - 1), fill=cat_lt)
        draw.point((cx + 19, cy - 2), fill=cat_lt)
        # six legs (animated run cycle)
        leg_positions = [5, 8, 10, 13, 15, 17]
        for i, lx in enumerate(leg_positions):
            off = (f + i) % 2
            draw.point((cx + lx, cy + 3), fill=cat_dk)
            draw.point((cx + lx, cy + 4 - off), fill=cat_dk)
            draw.point((cx + lx, cy + 5 - off), fill=cat_fur)

        frames.append(img)
    return frames


# ---------------------------------------------------------------------------
# Scene: RAIN — Forest with rain, puddles, Totoro at bus stop
# ---------------------------------------------------------------------------

def _scene_rain(num_frames: int = 4) -> List[Image.Image]:
    frames = []
    sky_top = (50, 60, 85)
    sky_bot = (80, 90, 110)
    tree_dark = (30, 80, 40)
    tree_light = (45, 110, 55)
    trunk_c = (70, 50, 35)
    ground_c = (55, 75, 55)
    puddle_c = (70, 90, 120)
    rain_c = (130, 170, 220)
    umbrella_c = (200, 60, 50)

    for f in range(num_frames):
        img = Image.new("RGB", (64, 64))
        draw = ImageDraw.Draw(img)

        _gradient(draw, sky_top, sky_bot, 0, 36)
        _gradient(draw, ground_c, (40, 60, 40), 36, 52)

        # trees in background
        trees = [(5, 18, 10), (20, 15, 12), (45, 17, 11), (58, 20, 8)]
        for tx, ty, th in trees:
            for y in range(ty + th, 42):
                draw.point((tx + 2, y), fill=trunk_c)
                draw.point((tx + 3, y), fill=trunk_c)
            draw.ellipse([tx - 3, ty, tx + 8, ty + th], fill=tree_dark)
            draw.ellipse([tx - 1, ty - 2, tx + 6, ty + th - 3], fill=tree_light)

        # rain drops (different positions per frame)
        rng = random.Random(42 + f)
        for _ in range(50):
            rx = rng.randint(0, 63)
            ry = rng.randint(0, 48)
            length = rng.randint(2, 4)
            draw.line([(rx, ry), (rx - 1, ry + length)], fill=rain_c)

        # puddles on ground
        puddles = [(8, 44), (25, 46), (42, 43), (55, 45)]
        for px, py in puddles:
            ripple = f % 3
            draw.ellipse([px - 4, py, px + 4, py + 2], fill=puddle_c)
            if ripple == 0:
                draw.arc([px - 3, py - 1, px + 3, py + 1], 0, 180,
                         fill=(150, 180, 220))

        # Bus stop sign — detailed
        pole_c = (120, 100, 80)
        sign_c = (180, 160, 60)
        sign_txt = (80, 70, 40)
        draw.line([(22, 28), (22, 46)], fill=pole_c)
        draw.line([(23, 28), (23, 46)], fill=(100, 80, 60))
        draw.rectangle([19, 25, 26, 29], fill=sign_c)
        draw.point((21, 27), fill=sign_txt)
        draw.point((23, 27), fill=sign_txt)
        draw.point((25, 27), fill=sign_txt)

        # Totoro at the bus stop — detailed pixel art (~12x18)
        t_body = (120, 130, 135)
        t_light = (145, 155, 160)
        t_dark = (85, 95, 100)
        t_belly = (195, 200, 185)
        t_chev = (70, 80, 85)
        t_eye_w = (200, 215, 230)
        t_pupil = (20, 20, 25)
        t_nose = (70, 75, 80)
        handle_c = (80, 60, 50)
        tx, ty = 30, 24
        # umbrella — rounded canopy with highlight
        draw.ellipse([tx - 1, ty - 6, tx + 12, ty + 1], fill=umbrella_c)
        draw.ellipse([tx + 1, ty - 5, tx + 10, ty - 2], fill=(220, 80, 70))
        # umbrella handle
        draw.line([(tx + 5, ty + 1), (tx + 5, ty + 3)], fill=handle_c)
        draw.point((tx + 4, ty + 3), fill=handle_c)
        # pointed ears
        draw.point((tx, ty + 2), fill=t_body)
        draw.point((tx + 1, ty + 2), fill=t_light)
        draw.point((tx + 9, ty + 2), fill=t_light)
        draw.point((tx + 10, ty + 2), fill=t_body)
        # head
        for dx in range(1, 10):
            draw.point((tx + dx, ty + 3), fill=t_body)
        for dx in range(0, 11):
            draw.point((tx + dx, ty + 4), fill=t_body)
        for dx in range(0, 11):
            draw.point((tx + dx, ty + 5), fill=t_body)
        # eyes with pupils and highlights
        draw.point((tx + 2, ty + 4), fill=t_eye_w)
        draw.point((tx + 3, ty + 4), fill=t_eye_w)
        draw.point((tx + 3, ty + 5), fill=t_pupil)
        draw.point((tx + 7, ty + 4), fill=t_eye_w)
        draw.point((tx + 8, ty + 4), fill=t_eye_w)
        draw.point((tx + 7, ty + 5), fill=t_pupil)
        draw.point((tx + 2, ty + 3), fill=(255, 255, 255))
        draw.point((tx + 8, ty + 3), fill=(255, 255, 255))
        # nose
        draw.point((tx + 5, ty + 5), fill=t_nose)
        # mouth
        for dx in range(1, 10):
            draw.point((tx + dx, ty + 6), fill=t_body)
        draw.point((tx + 3, ty + 6), fill=t_dark)
        draw.point((tx + 7, ty + 6), fill=t_dark)
        # body with shading
        for dy in range(7, 15):
            w = 11 if dy < 12 else 10 if dy < 14 else 8
            ox = 0 if dy < 14 else 1
            for dx in range(ox, w):
                draw.point((tx + dx, ty + dy), fill=t_body)
            draw.point((tx + ox, ty + dy), fill=t_dark)
            if dy < 14:
                draw.point((tx + w - 1, ty + dy), fill=t_dark)
        # shoulder highlight
        draw.point((tx + 1, ty + 7), fill=t_light)
        draw.point((tx + 2, ty + 7), fill=t_light)
        # arm holding umbrella (raised right arm)
        draw.point((tx + 9, ty + 7), fill=t_body)
        draw.point((tx + 10, ty + 6), fill=t_body)
        draw.point((tx + 10, ty + 5), fill=t_body)
        # belly patch
        for dy in range(8, 13):
            for dx in range(2, 9):
                draw.point((tx + dx, ty + dy), fill=t_belly)
        # chevrons
        draw.point((tx + 5, ty + 8), fill=t_chev)
        draw.point((tx + 4, ty + 9), fill=t_chev)
        draw.point((tx + 6, ty + 9), fill=t_chev)
        draw.point((tx + 5, ty + 10), fill=t_chev)
        draw.point((tx + 4, ty + 11), fill=t_chev)
        draw.point((tx + 6, ty + 11), fill=t_chev)
        draw.point((tx + 5, ty + 12), fill=t_chev)
        # feet with claws
        for dx in [1, 2, 3]:
            draw.point((tx + dx, ty + 15), fill=t_body)
        for dx in [6, 7, 8]:
            draw.point((tx + dx, ty + 15), fill=t_body)
        draw.point((tx + 1, ty + 16), fill=t_dark)
        draw.point((tx + 3, ty + 16), fill=t_dark)
        draw.point((tx + 6, ty + 16), fill=t_dark)
        draw.point((tx + 8, ty + 16), fill=t_dark)

        # Satsuki next to Totoro — detailed (~6x10)
        sx, sy = tx - 7, ty + 8
        hair_c = (60, 45, 35)
        skin_c = (220, 190, 160)
        coat_c = (220, 180, 80)
        coat_dk = (190, 150, 60)
        boot_c = (100, 70, 50)
        # hair
        for dx in range(1, 5):
            draw.point((sx + dx, sy), fill=hair_c)
        draw.point((sx + 1, sy + 1), fill=hair_c)
        draw.point((sx + 4, sy + 1), fill=hair_c)
        # face
        draw.point((sx + 2, sy + 1), fill=skin_c)
        draw.point((sx + 3, sy + 1), fill=skin_c)
        draw.point((sx + 2, sy + 2), fill=skin_c)
        draw.point((sx + 3, sy + 2), fill=skin_c)
        # tiny eyes
        draw.point((sx + 2, sy + 1), fill=(40, 35, 30))
        draw.point((sx + 3, sy + 1), fill=(40, 35, 30))
        # yellow raincoat
        for dy in range(3, 7):
            for dx in range(0, 6):
                draw.point((sx + dx, sy + dy), fill=coat_c)
        # coat shading on sides
        for dy in range(3, 7):
            draw.point((sx, sy + dy), fill=coat_dk)
            draw.point((sx + 5, sy + dy), fill=coat_dk)
        # coat buttons
        draw.point((sx + 3, sy + 4), fill=(180, 140, 50))
        draw.point((sx + 3, sy + 5), fill=(180, 140, 50))
        # boots
        draw.point((sx + 1, sy + 7), fill=boot_c)
        draw.point((sx + 2, sy + 7), fill=boot_c)
        draw.point((sx + 3, sy + 7), fill=boot_c)
        draw.point((sx + 4, sy + 7), fill=boot_c)

        frames.append(img)
    return frames


# ---------------------------------------------------------------------------
# Scene: SNOW — Cozy village with falling snowflakes
# ---------------------------------------------------------------------------

def _scene_snow(num_frames: int = 4) -> List[Image.Image]:
    frames = []
    sky_top = (80, 90, 110)
    sky_bot = (130, 140, 155)
    snow_ground = (220, 225, 235)
    snow_shadow = (180, 190, 210)
    house_wall = (160, 120, 80)
    house_roof = (120, 70, 50)
    window_glow = (255, 220, 130)
    tree_c = (60, 50, 45)

    for f in range(num_frames):
        img = Image.new("RGB", (64, 64))
        draw = ImageDraw.Draw(img)

        _gradient(draw, sky_top, sky_bot, 0, 32)
        _gradient(draw, snow_shadow, snow_ground, 32, 52)

        # distant hills with snow
        for x in range(64):
            hy = 28 + int(5 * ((x - 30) / 50) ** 2)
            for y in range(hy, 34):
                draw.point((x, y), fill=_lerp_color(sky_bot, snow_shadow, 0.5))

        # cozy house
        draw.rectangle([20, 28, 38, 42], fill=house_wall)
        # roof
        for i in range(10):
            draw.line([(20 - i // 2, 28 - i), (38 + i // 2, 28 - i)],
                      fill=house_roof)
        draw.rectangle([18, 19, 40, 28], fill=house_roof)
        # snow on roof
        draw.line([(18, 19), (40, 19)], fill=snow_ground)
        draw.line([(19, 20), (39, 20)], fill=snow_ground)
        # window with warm glow
        draw.rectangle([25, 32, 29, 36], fill=window_glow)
        draw.rectangle([31, 32, 35, 36], fill=window_glow)
        # door
        draw.rectangle([28, 38, 31, 42], fill=(100, 70, 45))
        # chimney
        draw.rectangle([35, 14, 38, 20], fill=(100, 80, 60))

        # bare tree
        for y in range(24, 44):
            draw.point((10, y), fill=tree_c)
        draw.line([(10, 26), (6, 22)], fill=tree_c)
        draw.line([(10, 28), (14, 24)], fill=tree_c)
        draw.line([(10, 32), (7, 28)], fill=tree_c)
        # snow on branches
        draw.point((6, 21), fill=snow_ground)
        draw.point((14, 23), fill=snow_ground)
        draw.point((7, 27), fill=snow_ground)

        # snowflakes
        rng = random.Random(100 + f)
        for _ in range(30):
            sx = rng.randint(0, 63)
            sy = rng.randint(0, 50)
            draw.point((sx, sy), fill=(240, 245, 255))

        # smoke from chimney (animated)
        smoke_x = 36 + (f % 2)
        for sy in range(8, 14):
            draw.point((smoke_x + (sy % 2), sy), fill=(180, 185, 195))

        # Calcifer on firewood — detailed pixel art (~10x14)
        cx, cy = 48, 34
        # firewood logs
        log_dk = (90, 55, 30)
        log_lt = (120, 80, 45)
        log_hi = (140, 100, 60)
        bark = (70, 40, 20)
        ash_c = (60, 55, 50)
        ember = (180, 60, 20)
        # left log (angled)
        for dx in range(-4, 2):
            draw.point((cx + dx, cy + 8), fill=log_dk)
            draw.point((cx + dx, cy + 9), fill=log_lt)
            draw.point((cx + dx, cy + 10), fill=log_dk)
        draw.point((cx - 4, cy + 9), fill=bark)
        draw.point((cx + 1, cy + 9), fill=bark)
        # right log (angled other way)
        for dx in range(-1, 5):
            draw.point((cx + dx, cy + 9), fill=log_lt)
            draw.point((cx + dx, cy + 10), fill=log_dk)
            draw.point((cx + dx, cy + 11), fill=log_dk)
        draw.point((cx + 4, cy + 10), fill=bark)
        draw.point((cx - 1, cy + 10), fill=bark)
        # cross piece
        draw.point((cx, cy + 9), fill=log_hi)
        draw.point((cx + 1, cy + 9), fill=log_hi)
        # glowing embers under logs
        draw.point((cx - 2, cy + 11), fill=ember)
        draw.point((cx + 1, cy + 11), fill=ember)
        draw.point((cx + 3, cy + 11), fill=(200, 80, 30))
        # ash
        draw.point((cx - 3, cy + 11), fill=ash_c)
        draw.point((cx + 4, cy + 12), fill=ash_c)

        # Calcifer — flame body with face (flickers per frame)
        flame_core = (255, 200, 50)
        flame_mid = (255, 140, 30)
        flame_outer = (230, 80, 20)
        flame_tip = (255, 240, 100)
        flame_dk = (200, 60, 15)
        eye_w = (240, 245, 250)
        eye_pupil = (20, 20, 25)
        mouth = (200, 50, 15)
        flicker = f % 2
        # flame base (wide, sitting on logs)
        for dx in range(-3, 4):
            draw.point((cx + dx, cy + 7), fill=flame_outer)
        for dx in range(-3, 4):
            draw.point((cx + dx, cy + 6), fill=flame_mid)
        for dx in range(-2, 3):
            draw.point((cx + dx, cy + 5), fill=flame_mid)
        # warm core
        for dx in range(-2, 3):
            draw.point((cx + dx, cy + 6), fill=flame_core)
            draw.point((cx + dx, cy + 5), fill=flame_core)
        for dx in range(-1, 2):
            draw.point((cx + dx, cy + 4), fill=flame_core)
        # upper flame (narrows, animated flicker)
        for dx in range(-2, 3):
            draw.point((cx + dx, cy + 3), fill=flame_mid)
        for dx in range(-1, 2):
            draw.point((cx + dx, cy + 2), fill=flame_mid)
        draw.point((cx + flicker, cy + 1), fill=flame_outer)
        draw.point((cx - 1 + flicker, cy + 1), fill=flame_outer)
        # flame tip (dances)
        draw.point((cx + flicker, cy), fill=flame_tip)
        draw.point((cx - 1 + flicker, cy - 1), fill=flame_tip)
        # side licks of flame
        draw.point((cx - 3, cy + 5), fill=flame_outer)
        draw.point((cx + 3, cy + 5), fill=flame_outer)
        draw.point((cx - 3 - flicker, cy + 4), fill=flame_dk)
        draw.point((cx + 3 + flicker, cy + 4), fill=flame_dk)
        # big round eyes (Calcifer's signature)
        draw.point((cx - 1, cy + 4), fill=eye_w)
        draw.point((cx - 2, cy + 4), fill=eye_w)
        draw.point((cx - 1, cy + 5), fill=eye_w)
        draw.point((cx - 2, cy + 5), fill=eye_pupil)
        draw.point((cx + 1, cy + 4), fill=eye_w)
        draw.point((cx + 2, cy + 4), fill=eye_w)
        draw.point((cx + 1, cy + 5), fill=eye_w)
        draw.point((cx + 2, cy + 5), fill=eye_pupil)
        # highlight in eyes
        draw.point((cx - 1, cy + 4), fill=(255, 255, 255))
        draw.point((cx + 1, cy + 4), fill=(255, 255, 255))
        # wide grin
        draw.point((cx - 2, cy + 6), fill=mouth)
        draw.point((cx - 1, cy + 7), fill=mouth)
        draw.point((cx, cy + 7), fill=mouth)
        draw.point((cx + 1, cy + 7), fill=mouth)
        draw.point((cx + 2, cy + 6), fill=mouth)
        # warm glow on nearby snow
        for gx in range(-5, 6):
            gy = cy + 12
            if 0 <= cx + gx < 64 and gy < 52:
                base = img.getpixel((cx + gx, gy))
                draw.point((cx + gx, gy),
                           fill=_blend(base, (255, 180, 80), 0.15))

        frames.append(img)
    return frames


# ---------------------------------------------------------------------------
# Scene: THUNDERSTORM — Dark sky, lightning, Kiki flying
# ---------------------------------------------------------------------------

def _scene_thunderstorm(num_frames: int = 4) -> List[Image.Image]:
    frames = []
    sky_top = (25, 25, 50)
    sky_bot = (50, 45, 70)
    cloud_dark = (60, 55, 75)
    cloud_light = (90, 85, 110)
    ground_c = (40, 55, 40)
    rain_c = (100, 140, 200)
    lightning_c = (255, 255, 180)

    for f in range(num_frames):
        img = Image.new("RGB", (64, 64))
        draw = ImageDraw.Draw(img)

        _gradient(draw, sky_top, sky_bot, 0, 36)
        _gradient(draw, ground_c, (30, 45, 30), 36, 52)

        # heavy clouds
        draw.ellipse([0, 6, 20, 16], fill=cloud_dark)
        draw.ellipse([10, 3, 35, 15], fill=cloud_light)
        draw.ellipse([25, 5, 50, 17], fill=cloud_dark)
        draw.ellipse([40, 3, 63, 14], fill=cloud_light)
        draw.rectangle([5, 12, 58, 17], fill=cloud_dark)

        # lightning bolt on alternating frames
        if f % 2 == 0:
            bolt = [(30, 17), (27, 24), (32, 24), (25, 35)]
            draw.line(bolt, fill=lightning_c, width=1)
            draw.line([(31, 17), (28, 24), (33, 24), (26, 35)],
                      fill=(255, 255, 220), width=1)
            # flash effect on ground
            for x in range(20, 40):
                base = img.getpixel((x, 36))
                img.putpixel((x, 36), _blend(base, (200, 200, 180), 0.3))

        # heavy rain
        rng = random.Random(200 + f)
        for _ in range(70):
            rx = rng.randint(0, 63)
            ry = rng.randint(14, 50)
            draw.line([(rx, ry), (rx - 1, ry + 3)], fill=rain_c)

        # silhouette of hills
        for x in range(64):
            hy = 38 + int(4 * ((x - 32) / 45) ** 2)
            for y in range(hy, 42):
                draw.point((x, y), fill=(35, 50, 35))

        # Kiki flying on her broom with Jiji — detailed pixel art (~22x12)
        kx = (44 - f * 7) % 46 + 8
        ky = 22 + (f % 3) - 1
        dress = (90, 40, 70)
        dress_dk = (65, 25, 50)
        skin = (220, 185, 160)
        hair = (50, 35, 30)
        hair_hi = (75, 55, 45)
        bow = (200, 60, 80)
        bow_dk = (160, 40, 60)
        broom_c = (140, 100, 50)
        broom_dk = (110, 75, 35)
        bristle_c = (180, 140, 60)
        bristle_lt = (200, 170, 90)
        jj = (25, 20, 30)
        jj_hi = (45, 40, 55)
        jj_eye = (220, 200, 80)
        # broom stick (long, with wood grain)
        draw.line([(kx - 7, ky + 5), (kx + 12, ky + 5)], fill=broom_c)
        draw.line([(kx - 7, ky + 6), (kx + 12, ky + 6)], fill=broom_dk)
        # broom bristles (fan shaped)
        for dy in range(-2, 3):
            draw.point((kx + 13, ky + 5 + dy), fill=bristle_c)
            draw.point((kx + 14, ky + 5 + dy), fill=bristle_c)
        draw.point((kx + 15, ky + 4), fill=bristle_lt)
        draw.point((kx + 15, ky + 6), fill=bristle_lt)
        draw.point((kx + 15, ky + 5), fill=bristle_c)
        # Kiki — flowing hair
        draw.point((kx - 1, ky - 3), fill=hair)
        draw.point((kx, ky - 3), fill=hair)
        draw.point((kx + 1, ky - 3), fill=hair)
        draw.point((kx - 2, ky - 2), fill=hair)
        draw.point((kx - 1, ky - 2), fill=hair)
        draw.point((kx, ky - 2), fill=hair)
        draw.point((kx + 1, ky - 2), fill=hair_hi)
        draw.point((kx - 3, ky - 1), fill=hair)
        # face
        draw.point((kx - 1, ky - 1), fill=skin)
        draw.point((kx, ky - 1), fill=skin)
        # eyes
        draw.point((kx - 1, ky - 1), fill=(40, 35, 30))
        draw.point((kx, ky - 1), fill=skin)
        draw.point((kx + 1, ky - 1), fill=skin)
        # big red bow
        draw.point((kx + 2, ky - 3), fill=bow)
        draw.point((kx + 3, ky - 3), fill=bow)
        draw.point((kx + 2, ky - 2), fill=bow_dk)
        draw.point((kx + 3, ky - 2), fill=bow)
        draw.point((kx + 4, ky - 3), fill=bow)
        # dress body
        for dx in range(-2, 3):
            draw.point((kx + dx, ky), fill=dress)
            draw.point((kx + dx, ky + 1), fill=dress)
        draw.point((kx - 2, ky + 2), fill=dress)
        draw.point((kx - 1, ky + 2), fill=dress)
        draw.point((kx, ky + 2), fill=dress)
        draw.point((kx + 1, ky + 2), fill=dress)
        draw.point((kx + 2, ky + 2), fill=dress)
        # dress shading
        draw.point((kx - 2, ky + 1), fill=dress_dk)
        draw.point((kx + 2, ky + 1), fill=dress_dk)
        # dress fluttering in wind
        draw.point((kx + 3, ky + 2), fill=dress)
        draw.point((kx + 3, ky + 3), fill=dress_dk)
        # arms reaching forward on broom
        draw.point((kx + 2, ky + 3), fill=skin)
        draw.point((kx + 3, ky + 4), fill=skin)
        # legs dangling
        draw.point((kx - 1, ky + 3), fill=skin)
        draw.point((kx - 1, ky + 4), fill=skin)
        draw.point((kx + 1, ky + 3), fill=skin)
        draw.point((kx + 1, ky + 4), fill=skin)
        # shoes
        draw.point((kx - 1, ky + 5), fill=(60, 30, 25))
        draw.point((kx + 1, ky + 5), fill=(60, 30, 25))
        # Jiji (black cat) sitting behind Kiki — detailed
        jx = kx - 5
        # head
        draw.point((jx, ky + 1), fill=jj)
        draw.point((jx + 1, ky + 1), fill=jj)
        draw.point((jx + 2, ky + 1), fill=jj)
        draw.point((jx, ky + 2), fill=jj)
        draw.point((jx + 1, ky + 2), fill=jj)
        draw.point((jx + 2, ky + 2), fill=jj)
        # pointed ears
        draw.point((jx, ky), fill=jj)
        draw.point((jx + 2, ky), fill=jj)
        # golden eyes
        draw.point((jx, ky + 2), fill=jj_eye)
        draw.point((jx + 2, ky + 2), fill=jj_eye)
        # body (arched back)
        draw.point((jx, ky + 3), fill=jj)
        draw.point((jx + 1, ky + 3), fill=jj_hi)
        draw.point((jx + 2, ky + 3), fill=jj)
        draw.point((jx + 1, ky + 4), fill=jj)
        # paws on broom
        draw.point((jx, ky + 4), fill=jj)
        draw.point((jx + 2, ky + 4), fill=jj)
        # curled tail
        draw.point((jx - 1, ky + 3), fill=jj)
        draw.point((jx - 2, ky + 2), fill=jj)
        draw.point((jx - 2, ky + 1), fill=jj)

        frames.append(img)
    return frames


# ---------------------------------------------------------------------------
# Scene: FOG — Misty mountains, faint trees
# ---------------------------------------------------------------------------

def _scene_fog(num_frames: int = 4) -> List[Image.Image]:
    frames = []
    sky_top = (150, 160, 170)
    sky_bot = (170, 175, 180)
    mist = (165, 170, 178)
    tree_c = (100, 115, 105)
    ground_c = (130, 140, 130)

    for f in range(num_frames):
        img = Image.new("RGB", (64, 64))
        draw = ImageDraw.Draw(img)

        _gradient(draw, sky_top, sky_bot, 0, 52)

        # faint mountain silhouettes
        for x in range(64):
            m1 = 20 + int(12 * abs((x - 25) / 40) ** 1.5)
            for y in range(m1, 40):
                base = img.getpixel((x, y))
                draw.point((x, y), fill=_blend(base, (120, 130, 125), 0.3))

        # fog layers that shift per frame
        fog_layers = [
            (22 + f, 0.25), (30 - f, 0.35), (38 + f % 2, 0.4), (44 - f % 3, 0.3),
        ]
        for fy, alpha in fog_layers:
            for y in range(max(0, fy), min(64, fy + 4)):
                for x in range(64):
                    base = img.getpixel((x, y))
                    draw.point((x, y), fill=_blend(base, mist, alpha))

        # ghostly trees
        ghost_trees = [(12, 28), (35, 30), (52, 26)]
        for tx, ty in ghost_trees:
            for y in range(ty, ty + 14):
                draw.point((tx, y), fill=_blend(mist, tree_c, 0.4))
                draw.point((tx + 1, y), fill=_blend(mist, tree_c, 0.3))
            draw.ellipse([tx - 4, ty - 5, tx + 5, ty + 3],
                         fill=_blend(mist, tree_c, 0.35))

        # ground
        _gradient(draw, ground_c, (140, 148, 138), 44, 52)

        # Kodama (tree spirits) — detailed pixel art with head-tilt
        k_head = (230, 235, 225)
        k_head_hi = (245, 248, 240)
        k_head_sh = (200, 205, 195)
        k_hole = (60, 70, 60)
        k_body = (200, 210, 200)
        k_body_dk = (170, 180, 170)
        k_glow = (210, 230, 210)
        tilt_seq = [0, -1, 0, 1]
        spirits = [(12, 34), (24, 32), (40, 35), (53, 33)]
        for i, (kx, ky) in enumerate(spirits):
            tilt = tilt_seq[(f + i) % 4]
            hx = kx + tilt

            if tilt == 0:
                # upright — symmetric round head
                draw.point((hx, ky), fill=k_head_hi)
                for dx in range(-1, 2):
                    draw.point((hx + dx, ky + 1), fill=k_head)
                for dx in range(-2, 3):
                    draw.point((hx + dx, ky + 2), fill=k_head)
                for dx in range(-2, 3):
                    draw.point((hx + dx, ky + 3), fill=k_head)
                for dx in range(-1, 2):
                    draw.point((hx + dx, ky + 4), fill=k_head)
                draw.point((hx - 1, ky + 1), fill=k_head_hi)
                draw.point((hx + 2, ky + 2), fill=k_head_sh)
                draw.point((hx + 2, ky + 3), fill=k_head_sh)
                # face
                draw.point((hx - 1, ky + 2), fill=k_hole)
                draw.point((hx + 1, ky + 2), fill=k_hole)
                draw.point((hx, ky + 3), fill=k_hole)
            elif tilt == -1:
                # tilted left — left side droops lower
                draw.point((hx + 1, ky), fill=k_head_hi)
                draw.point((hx, ky + 1), fill=k_head)
                draw.point((hx + 1, ky + 1), fill=k_head)
                draw.point((hx + 2, ky + 1), fill=k_head)
                for dx in range(-2, 3):
                    draw.point((hx + dx, ky + 2), fill=k_head)
                for dx in range(-2, 3):
                    draw.point((hx + dx, ky + 3), fill=k_head)
                draw.point((hx - 2, ky + 4), fill=k_head)
                draw.point((hx - 1, ky + 4), fill=k_head)
                draw.point((hx, ky + 4), fill=k_head)
                draw.point((hx + 1, ky + 4), fill=k_head)
                draw.point((hx - 2, ky + 5), fill=k_head)
                draw.point((hx - 1, ky + 5), fill=k_head_sh)
                draw.point((hx + 2, ky + 2), fill=k_head_sh)
                # face (shifted slightly with tilt)
                draw.point((hx - 1, ky + 3), fill=k_hole)
                draw.point((hx + 1, ky + 2), fill=k_hole)
                draw.point((hx, ky + 4), fill=k_hole)
            else:
                # tilted right — right side droops lower
                draw.point((hx - 1, ky), fill=k_head_hi)
                draw.point((hx - 2, ky + 1), fill=k_head)
                draw.point((hx - 1, ky + 1), fill=k_head)
                draw.point((hx, ky + 1), fill=k_head)
                for dx in range(-2, 3):
                    draw.point((hx + dx, ky + 2), fill=k_head)
                for dx in range(-2, 3):
                    draw.point((hx + dx, ky + 3), fill=k_head)
                draw.point((hx - 1, ky + 4), fill=k_head)
                draw.point((hx, ky + 4), fill=k_head)
                draw.point((hx + 1, ky + 4), fill=k_head)
                draw.point((hx + 2, ky + 4), fill=k_head)
                draw.point((hx + 1, ky + 5), fill=k_head_sh)
                draw.point((hx + 2, ky + 5), fill=k_head)
                draw.point((hx - 2, ky + 2), fill=k_head_sh)
                # face (shifted slightly with tilt)
                draw.point((hx - 1, ky + 2), fill=k_hole)
                draw.point((hx + 1, ky + 3), fill=k_hole)
                draw.point((hx, ky + 4), fill=k_hole)

            # neck stays centered on body
            draw.point((kx, ky + 5), fill=k_body)
            # body (always upright)
            draw.point((kx - 1, ky + 6), fill=k_body)
            draw.point((kx, ky + 6), fill=k_body)
            draw.point((kx + 1, ky + 6), fill=k_body)
            draw.point((kx - 1, ky + 7), fill=k_body)
            draw.point((kx, ky + 7), fill=k_body)
            draw.point((kx + 1, ky + 7), fill=k_body)
            draw.point((kx, ky + 8), fill=k_body)
            draw.point((kx + 1, ky + 7), fill=k_body_dk)
            draw.point((kx - 2, ky + 6), fill=k_body)
            draw.point((kx + 2, ky + 6), fill=k_body)
            draw.point((hx, ky - 1), fill=k_glow)

        frames.append(img)
    return frames


# ---------------------------------------------------------------------------
# Scene dispatcher
# ---------------------------------------------------------------------------

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


SCENE_DISPATCH = {
    "clear": _scene_sunny,
    "cloudy": _scene_cloudy,
    "rain": _scene_rain,
    "snow": _scene_snow,
    "thunderstorm": _scene_thunderstorm,
    "fog": _scene_fog,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_weather(data: WeatherData) -> List[Image.Image]:
    """Return a list of animated 64x64 frames for the current weather."""
    condition = _condition_from_code(data.weather_code)
    scene_fn = SCENE_DISPATCH.get(condition, _scene_cloudy)
    raw_frames = scene_fn()
    return [_apply_overlay(frame, data) for frame in raw_frames]

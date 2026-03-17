"""Send a rendered PNG to the iDotMatrix 64x64 display pixel-by-pixel over BLE.

The 64x64 display doesn't support the library's PNG image upload protocol,
so we use FullscreenColor to paint the background, then Graffiti to draw
only the non-background pixels.
"""

import asyncio
import logging

from PIL import Image

from idotmatrix import ConnectionManager, FullscreenColor, Graffiti

import config

log = logging.getLogger(__name__)

MAX_RETRIES = 2


async def _upload(png_path: str) -> None:
    conn = ConnectionManager()

    if config.BLE_ADDRESS:
        log.info("connecting to iDotMatrix at %s", config.BLE_ADDRESS)
        await conn.connectByAddress(config.BLE_ADDRESS)
    else:
        log.info("scanning for iDotMatrix device...")
        await conn.connectBySearch()

    img = Image.open(png_path).convert("RGB")
    pixels = img.load()
    size = config.DISPLAY_SIZE
    bg = pixels[0, 0]

    log.info("filling background with (%d, %d, %d)", *bg)
    fs = FullscreenColor()
    await fs.setMode(r=bg[0], g=bg[1], b=bg[2])
    await asyncio.sleep(0.3)

    graffiti = Graffiti()
    drawn = 0
    skipped = 0
    for y in range(size):
        for x in range(size):
            r, g, b = pixels[x, y]
            if (r, g, b) == bg:
                skipped += 1
                continue
            await graffiti.setPixel(r=r, g=g, b=b, x=x, y=y)
            drawn += 1
            await asyncio.sleep(config.BLE_PIXEL_DELAY)

    log.info("done — drew %d pixels, skipped %d background pixels", drawn, skipped)


def send_to_display(png_path: str) -> None:
    """Upload *png_path* to the iDotMatrix display, retrying on failure."""
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            asyncio.run(_upload(png_path))
            return
        except Exception as exc:
            last_err = exc
            log.warning("attempt %d/%d failed: %s", attempt, MAX_RETRIES, exc)
    raise RuntimeError(f"failed after {MAX_RETRIES} attempts") from last_err

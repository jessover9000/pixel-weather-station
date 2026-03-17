#!/usr/bin/env python3
"""Pixel Weather Station — animated Ghibli-style weather on iDotMatrix 64x64."""

import asyncio
import logging
import signal
import sys
import time

import config
from weather import fetch_weather
from renderer import render_weather
from display import send_frames, _find_device

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("weather_station")

_shutdown = False


def _handle_signal(*_):
    global _shutdown
    _shutdown = True
    log.info("shutdown requested")


async def run() -> int:
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    from bleak import BleakClient
    address = config.BLE_ADDRESS or await _find_device()

    last_fetch = 0.0

    while not _shutdown:
        now = time.monotonic()
        if now - last_fetch >= config.WEATHER_REFRESH_INTERVAL or last_fetch == 0.0:
            try:
                log.info("fetching weather for Darmstadt...")
                data = fetch_weather()
                log.info(
                    "current=%.1f°C  max=%.1f°C  rain=%d%%  code=%d",
                    data.current_temp, data.max_temp,
                    data.max_rain_probability, data.weather_code,
                )
                frames = render_weather(data)
                log.info("rendered %d animation frames", len(frames))
                last_fetch = time.monotonic()
            except Exception:
                log.exception("failed to fetch/render weather — retrying in 60s")
                await asyncio.sleep(60)
                continue

        try:
            log.info("connecting to display at %s ...", address)
            async with BleakClient(address, timeout=15) as client:
                from display import WRITE_CHAR_UUID, SET_DRAW_MODE, _send_frame
                log.info("connected — sending SetDrawMode(1)")
                await client.write_gatt_char(WRITE_CHAR_UUID, SET_DRAW_MODE, response=True)
                await asyncio.sleep(0.1)

                while not _shutdown:
                    if time.monotonic() - last_fetch >= config.WEATHER_REFRESH_INTERVAL:
                        log.info("time to refresh weather — reconnecting")
                        break

                    for frame in frames:
                        if _shutdown:
                            break
                        await _send_frame(client, frame)
                        await asyncio.sleep(config.FRAME_DELAY)

        except Exception:
            log.exception("display error — retrying in 10s")
            await asyncio.sleep(10)

    log.info("goodbye")
    return 0


def main() -> int:
    try:
        return asyncio.run(run())
    except KeyboardInterrupt:
        log.info("interrupted")
        return 0


if __name__ == "__main__":
    sys.exit(main())

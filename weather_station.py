#!/usr/bin/env python3
"""Pixel Weather Station — fetch weather, render, and push to iDotMatrix."""

import logging
import sys

import config
from weather import fetch_weather
from renderer import render_weather
from display import send_to_display

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("weather_station")


def main() -> int:
    try:
        log.info("fetching weather for Darmstadt...")
        data = fetch_weather()
        log.info(
            "current=%.1f°C  max=%.1f°C  rain=%d%%  code=%d",
            data.current_temp, data.max_temp,
            data.max_rain_probability, data.weather_code,
        )
    except Exception:
        log.exception("failed to fetch weather data")
        return 1

    try:
        path = render_weather(data, config.OUTPUT_PATH)
        log.info("rendered image to %s", path)
    except Exception:
        log.exception("failed to render weather image")
        return 1

    try:
        send_to_display(path)
        log.info("display updated successfully")
    except Exception:
        log.exception("failed to send image to display")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

# Pixel Weather Station

A cute pixel-art weather display for the **iDotMatrix 64x64** LED panel.
Fetches live weather for Darmstadt, Germany from the Open-Meteo API, renders a
64x64 image with pixel-art icons and bitmap fonts, and pushes it to the display
over Bluetooth every 15 minutes.

## What it shows

| Data               | Source                                       |
|--------------------|----------------------------------------------|
| Current temp       | Open-Meteo `current.temperature_2m`          |
| Max temp (today)   | Open-Meteo `daily.temperature_2m_max`        |
| Max rain prob <6pm | Open-Meteo `hourly.precipitation_probability`|
| Weather icon       | Mapped from WMO weather code                 |

Weather icons: sun, clouds, rain, snow, fog, thunderstorm. A decorative grass
strip with tiny flowers lines the bottom of the display.

## Setup

### 1. Install dependencies

```bash
cd pixel-weather-station
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Pair your iDotMatrix display

Open **System Settings > Bluetooth** on macOS and pair the iDotMatrix display.
The script will auto-discover it over BLE.

If auto-discovery is slow, find the BLE address (it looks like `AA:BB:CC:DD:EE:FF`)
and set it in `config.py`:

```python
BLE_ADDRESS = "AA:BB:CC:DD:EE:FF"
```

### 3. Run manually

```bash
source .venv/bin/activate
python weather_station.py
```

### 4. Schedule automatic updates (every 15 minutes)

Copy the launch agent plist and load it:

```bash
cp com.pixel-weather.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.pixel-weather.plist
```

Check that the paths inside `com.pixel-weather.plist` match your setup
(Python venv path and project directory).

To stop the schedule:

```bash
launchctl unload ~/Library/LaunchAgents/com.pixel-weather.plist
```

Logs are written to `/tmp/pixel-weather-stdout.log` and `/tmp/pixel-weather-stderr.log`.

## Configuration

Edit `config.py` to change:

| Setting            | Default               | Description                           |
|--------------------|-----------------------|---------------------------------------|
| `LATITUDE`         | 49.8728               | Darmstadt latitude                    |
| `LONGITUDE`        | 8.6512                | Darmstadt longitude                   |
| `TIMEZONE`         | `Europe/Berlin`       | Timezone for hourly data              |
| `DISPLAY_SIZE`     | 64                    | Pixel dimension of the display        |
| `BLE_ADDRESS`      | `None`                | Set to skip auto-discovery            |
| `RAIN_CUTOFF_HOUR` | 18                    | Only count rain probability before 6pm|

## Project structure

```
config.py              Configuration constants
weather.py             Open-Meteo API client
renderer.py            64x64 pixel-art image renderer
display.py             iDotMatrix BLE upload wrapper
weather_station.py     Main entry point
com.pixel-weather.plist  macOS launchd schedule
```

## Dependencies

- **idotmatrix** — BLE communication with iDotMatrix displays
- **requests** — HTTP client for Open-Meteo
- **Pillow** — Image rendering

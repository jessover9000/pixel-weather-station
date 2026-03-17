LATITUDE = 49.8728
LONGITUDE = 8.6512
TIMEZONE = "Europe/Berlin"

DISPLAY_SIZE = 64

# Set to a BLE address string (e.g. "AA:BB:CC:DD:EE:FF") to skip auto-discovery,
# or leave as None to scan for the first iDotMatrix device.
BLE_ADDRESS = "1E01C326-54AC-5342-ADE1-E3037B4E30B1"

# Where the rendered PNG is temporarily saved before uploading
OUTPUT_PATH = "/tmp/pixel_weather.png"

# Open-Meteo base URL
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Hour cutoff for rain probability (18 = 6pm)
RAIN_CUTOFF_HOUR = 18

# Delay in seconds between BLE pixel writes to avoid packet loss
BLE_PIXEL_DELAY = 0.02

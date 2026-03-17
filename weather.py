from dataclasses import dataclass
from datetime import datetime

import requests

import config


@dataclass
class WeatherData:
    current_temp: float
    max_temp: float
    max_rain_probability: int
    weather_code: int
    sunrise: datetime
    sunset: datetime


def _weather_code_to_condition(code: int) -> str:
    """Map WMO weather code to a simplified condition string for icon selection."""
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


def fetch_weather() -> WeatherData:
    params = {
        "latitude": config.LATITUDE,
        "longitude": config.LONGITUDE,
        "current": "temperature_2m,weather_code",
        "hourly": "precipitation_probability",
        "daily": "temperature_2m_max,sunrise,sunset",
        "timezone": config.TIMEZONE,
        "forecast_days": 1,
    }

    resp = requests.get(config.OPEN_METEO_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    current_temp = data["current"]["temperature_2m"]
    weather_code = data["current"]["weather_code"]
    max_temp = data["daily"]["temperature_2m_max"][0]

    hourly_times = data["hourly"]["time"]
    hourly_rain = data["hourly"]["precipitation_probability"]

    max_rain = 0
    for time_str, prob in zip(hourly_times, hourly_rain):
        hour = datetime.fromisoformat(time_str).hour
        if hour < config.RAIN_CUTOFF_HOUR and prob is not None:
            max_rain = max(max_rain, prob)

    sunrise = datetime.fromisoformat(data["daily"]["sunrise"][0])
    sunset = datetime.fromisoformat(data["daily"]["sunset"][0])

    return WeatherData(
        current_temp=current_temp,
        max_temp=max_temp,
        max_rain_probability=max_rain,
        weather_code=weather_code,
        sunrise=sunrise,
        sunset=sunset,
    )

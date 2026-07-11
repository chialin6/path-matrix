#!/usr/bin/env python3
import requests
from dataclasses import dataclass

from config import WEATHER_LAT, WEATHER_LON, RAIN_THRESHOLD_PCT, RAIN_LOOKAHEAD_HOURS

WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"


@dataclass
class WeatherData:
    feels_now: int
    feels_min: int
    feels_max: int
    rain_hour: str  # e.g. "3pm", or "" if no rain expected
    rain_prob: int  # peak probability, or 0 if no rain expected


def _format_hour(hour: int) -> str:
    if hour == 0:
        return "12am"
    elif hour < 12:
        return f"{hour}am"
    elif hour == 12:
        return "12pm"
    else:
        return f"{hour - 12}pm"


def get_weather() -> WeatherData:
    params = {
        "latitude": WEATHER_LAT,
        "longitude": WEATHER_LON,
        "current": "apparent_temperature",
        "daily": "apparent_temperature_max,apparent_temperature_min",
        "hourly": "precipitation_probability",
        "timezone": "America/New_York",
        "forecast_days": 1,
    }
    resp = requests.get(WEATHER_API_URL, params=params, timeout=8)
    resp.raise_for_status()
    data = resp.json()

    feels_now = round(data["current"]["apparent_temperature"])
    feels_min = round(data["daily"]["apparent_temperature_min"][0])
    feels_max = round(data["daily"]["apparent_temperature_max"][0])

    hourly_times = data["hourly"]["time"]
    hourly_probs = data["hourly"]["precipitation_probability"]

    # Locate current hour in the hourly array
    current_hour_str = data["current"]["time"][:13] + ":00"
    try:
        current_idx = hourly_times.index(current_hour_str)
    except ValueError:
        current_idx = 0

    # Scan next 8 hours for peak rain probability
    window_times = hourly_times[current_idx: current_idx + RAIN_LOOKAHEAD_HOURS]
    window_probs = hourly_probs[current_idx: current_idx + RAIN_LOOKAHEAD_HOURS]

    rain_hour = ""
    rain_prob = 0
    if window_probs:
        peak_prob = max(window_probs)
        if peak_prob >= RAIN_THRESHOLD_PCT:
            peak_idx = window_probs.index(peak_prob)
            rain_hour = _format_hour(int(window_times[peak_idx][11:13]))
            rain_prob = peak_prob

    return WeatherData(
        feels_now=feels_now,
        feels_min=feels_min,
        feels_max=feels_max,
        rain_hour=rain_hour,
        rain_prob=rain_prob,
    )


if __name__ == "__main__":
    w = get_weather()
    print(f"Feels like: {w.feels_now}°C  (min {w.feels_min}°C / max {w.feels_max}°C)")
    if w.rain_hour:
        print(f"Rain: {w.rain_prob}% @ {w.rain_hour}")
    else:
        print("No rain expected in next 8h")

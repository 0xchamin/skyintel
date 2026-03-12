"""Fetch current weather from Open-Meteo API."""

import httpx
import logging

logger = logging.getLogger(__name__)

BASE_URL = "https://api.open-meteo.com/v1/forecast"


class OpenMeteoClient:
    def __init__(self):
        self._http = httpx.AsyncClient(timeout=15.0)

    async def get_current(self, lat: float, lon: float) -> dict | None:
        """Get current weather at a location."""
        try:
            resp = await self._http.get(BASE_URL, params={
                "latitude": lat,
                "longitude": lon,
                "current": ",".join([
                    "temperature_2m",
                    "relative_humidity_2m",
                    "apparent_temperature",
                    "wind_speed_10m",
                    "wind_direction_10m",
                    "wind_gusts_10m",
                    "cloud_cover",
                    #"visibility",
                    "precipitation",
                    "weather_code",
                ]),
                "wind_speed_unit": "kn",
                "temperature_unit": "celsius",
            })
            resp.raise_for_status()
            data = resp.json()
            current = data.get("current", {})

            return {
                "temperature_c": current.get("temperature_2m"),
                "feels_like_c": current.get("apparent_temperature"),
                "humidity_pct": current.get("relative_humidity_2m"),
                "wind_speed_kt": current.get("wind_speed_10m"),
                "wind_direction": current.get("wind_direction_10m"),
                "wind_gusts_kt": current.get("wind_gusts_10m"),
                "cloud_cover_pct": current.get("cloud_cover"),
                #"visibility_m": current.get("visibility"),
                "precipitation_mm": current.get("precipitation"),
                "weather_code": current.get("weather_code"),
                "description": _weather_description(current.get("weather_code")),
            }
        except Exception as e:
            logger.error("Open-Meteo failed: %s", e)
            return None

    async def close(self):
        await self._http.aclose()


WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    77: "Snow grains",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    85: "Slight snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm + hail", 99: "Thunderstorm + heavy hail",
}


def _weather_description(code: int | None) -> str:
    if code is None:
        return "Unknown"
    return WMO_CODES.get(code, f"WMO {code}")

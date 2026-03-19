"""Fetch marine weather from Open-Meteo Marine API."""

import httpx
import logging

logger = logging.getLogger(__name__)

BASE_URL = "https://marine-api.open-meteo.com/v1/marine"


class MarineWeatherClient:
    def __init__(self):
        self._http = httpx.AsyncClient(timeout=15.0)

    async def get_current(self, lat: float, lon: float) -> dict | None:
        """Get current marine weather at a location."""
        try:
            resp = await self._http.get(BASE_URL, params={
                "latitude": lat,
                "longitude": lon,
                "current": ",".join([
                    "wave_height",
                    "wave_direction",
                    "wave_period",
                    "swell_wave_height",
                    "swell_wave_direction",
                    "swell_wave_period",
                    "wind_wave_height",
                    "wind_wave_direction",
                    "wind_wave_period",
                    "ocean_current_velocity",
                    "ocean_current_direction",
                ]),
                "length_unit": "metric",
            })
            resp.raise_for_status()
            data = resp.json()
            current = data.get("current", {})

            return {
                "wave_height_m": current.get("wave_height"),
                "wave_direction": current.get("wave_direction"),
                "wave_period_s": current.get("wave_period"),
                "swell_height_m": current.get("swell_wave_height"),
                "swell_direction": current.get("swell_wave_direction"),
                "swell_period_s": current.get("swell_wave_period"),
                "wind_wave_height_m": current.get("wind_wave_height"),
                "wind_wave_direction": current.get("wind_wave_direction"),
                "wind_wave_period_s": current.get("wind_wave_period"),
                "current_velocity_ms": current.get("ocean_current_velocity"),
                "current_direction": current.get("ocean_current_direction"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
            }
        except Exception as e:
            logger.error("Marine weather failed: %s", e)
            return None

    async def close(self):
        await self._http.aclose()

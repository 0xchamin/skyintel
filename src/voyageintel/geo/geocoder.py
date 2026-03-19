"""Google Maps Geocoding API client with SQLite cache."""

import logging
from datetime import datetime, timezone

import httpx
import aiosqlite

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
CACHE_TTL_DAYS = 30


class Geocoder:
    """Google Maps Geocoding with SQLite cache."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key
        self._http = httpx.AsyncClient(timeout=10.0)

    @property
    def available(self) -> bool:
        return self._api_key is not None

    async def geocode(self, place_name: str, db: aiosqlite.Connection) -> dict | None:
        """Resolve a place name to coordinates. Checks cache first.

        Returns dict with latitude, longitude, formatted_addr or None.
        """
        if not place_name or not place_name.strip():
            return None

        normalised = place_name.strip().lower()

        # Check cache
        cached = await self._cache_get(db, normalised)
        if cached:
            return cached

        # Call Google Maps API
        if not self._api_key:
            return None

        try:
            resp = await self._http.get(GEOCODE_URL, params={
                "address": place_name.strip(),
                "key": self._api_key,
            })
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "OK" or not data.get("results"):
                logger.debug("Geocode failed for '%s': %s", place_name, data.get("status"))
                return None

            result = data["results"][0]
            location = result["geometry"]["location"]
            formatted = result.get("formatted_address", place_name)

            geo = {
                "latitude": location["lat"],
                "longitude": location["lng"],
                "formatted_addr": formatted,
            }

            # Cache result
            await self._cache_put(db, normalised, geo)

            logger.info("Geocoded '%s' → (%.4f, %.4f)", place_name, geo["latitude"], geo["longitude"])
            return geo

        except Exception as e:
            logger.error("Geocode API failed for '%s': %s", place_name, e)
            return None

    async def _cache_get(self, db: aiosqlite.Connection, key: str) -> dict | None:
        """Get cached geocode result."""
        async with db.execute(
            "SELECT latitude, longitude, formatted_addr FROM geocode_cache WHERE place_name = ?",
            (key,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "latitude": row[0],
                    "longitude": row[1],
                    "formatted_addr": row[2],
                }
        return None

    async def _cache_put(self, db: aiosqlite.Connection, key: str, geo: dict):
        """Cache a geocode result."""
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            """
            INSERT OR REPLACE INTO geocode_cache (place_name, latitude, longitude, formatted_addr, cached_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (key, geo["latitude"], geo["longitude"], geo["formatted_addr"], now),
        )
        await db.commit()

    async def close(self):
        await self._http.aclose()

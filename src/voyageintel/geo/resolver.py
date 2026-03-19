"""Resolve place names to coordinates for AI queries."""

import logging

import aiosqlite

from voyageintel.geo.geocoder import Geocoder

logger = logging.getLogger(__name__)


class PlaceResolver:
    """Resolve place names to coordinates.

    Priority:
    1. SQLite geocode cache (instant)
    2. Google Maps API (if key available)
    3. Returns None (LLM falls back to built-in geography knowledge)
    """

    def __init__(self, geocoder: Geocoder):
        self._geocoder = geocoder

    async def resolve(self, place_name: str, db: aiosqlite.Connection) -> tuple[float, float] | None:
        """Resolve a place name to (lat, lon) tuple, or None if unavailable."""
        result = await self._geocoder.geocode(place_name, db)
        if result:
            return (result["latitude"], result["longitude"])
        return None

"""Aircraft metadata + route lookup via hexdb.io, with SQLite caching."""

import httpx
import logging
import aiosqlite
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

AIRCRAFT_URL = "https://hexdb.io/api/v1/aircraft/{hex}"
ROUTE_URL = "https://hexdb.io/callsign-route?callsign={callsign}"

# Cache TTL
AIRCRAFT_TTL_DAYS = 30
ROUTE_TTL_DAYS = 7


class HexdbClient:
    def __init__(self):
        self._http = httpx.AsyncClient(timeout=10.0)

    async def lookup_aircraft(self, icao24: str) -> dict | None:
        """Fetch aircraft metadata by ICAO24 hex code."""
        try:
            resp = await self._http.get(AIRCRAFT_URL.format(hex=icao24.upper()))
            if resp.status_code != 200:
                return None
            data = resp.json()
            return {
                "icao24": icao24.lower(),
                "registration": data.get("Registration"),
                "manufacturer": data.get("Manufacturer"),
                "type_code": data.get("ICAOTypeCode"),
                "type_name": data.get("Type"),
                "owner": data.get("RegisteredOwners"),
                "operator_code": data.get("OperatorFlagCode"),
            }
        except Exception as e:
            logger.debug("hexdb aircraft lookup failed for %s: %s", icao24, e)
            return None

    async def lookup_route(self, callsign: str) -> dict | None:
        """Fetch route (origin-destination) by callsign."""
        try:
            resp = await self._http.get(ROUTE_URL.format(callsign=callsign.strip().upper()))
            if resp.status_code != 200:
                return None
            text = resp.text.strip()
            if not text or "-" not in text:
                return None
            parts = text.split("-", 1)
            return {
                "callsign": callsign.strip().upper(),
                "origin_icao": parts[0].strip(),
                "destination_icao": parts[1].strip(),
            }
        except Exception as e:
            logger.debug("hexdb route lookup failed for %s: %s", callsign, e)
            return None

    async def close(self):
        await self._http.aclose()


# ── Cached lookups ───────────────────────────────────────────

async def get_aircraft_cached(db: aiosqlite.Connection, client: HexdbClient, icao24: str) -> dict | None:
    """Get aircraft metadata, using SQLite cache with TTL."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=AIRCRAFT_TTL_DAYS)).isoformat()
    async with db.execute(
        "SELECT icao24, registration, manufacturer, type_code, type_name, owner, operator_code "
        "FROM aircraft_meta WHERE icao24 = ? AND updated_at > ?",
        (icao24.lower(), cutoff),
    ) as cursor:
        row = await cursor.fetchone()
        if row:
            cols = [d[0] for d in cursor.description]
            return dict(zip(cols, row))

    # Cache miss — fetch from API
    data = await client.lookup_aircraft(icao24)
    if data:
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT OR REPLACE INTO aircraft_meta "
            "(icao24, registration, manufacturer, type_code, type_name, owner, operator_code, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (data["icao24"], data["registration"], data["manufacturer"],
             data["type_code"], data["type_name"], data["owner"], data["operator_code"], now),
        )
        await db.commit()
    return data


async def get_route_cached(db: aiosqlite.Connection, client: HexdbClient, callsign: str) -> dict | None:
    """Get flight route, using SQLite cache with TTL."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=ROUTE_TTL_DAYS)).isoformat()
    async with db.execute(
        "SELECT callsign, origin_icao, destination_icao "
        "FROM routes WHERE callsign = ? AND updated_at > ?",
        (callsign.strip().upper(), cutoff),
    ) as cursor:
        row = await cursor.fetchone()
        if row:
            cols = [d[0] for d in cursor.description]
            return dict(zip(cols, row))

    # Cache miss — fetch from API
    data = await client.lookup_route(callsign)
    if data:
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT OR REPLACE INTO routes (callsign, origin_icao, destination_icao, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (data["callsign"], data["origin_icao"], data["destination_icao"], now),
        )
        await db.commit()
    return data

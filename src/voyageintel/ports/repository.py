"""Port database — load from bundled JSON, spatial queries via R*Tree."""

import json
import logging
import hashlib
from pathlib import Path

import aiosqlite

from voyageintel.models import Port

logger = logging.getLogger(__name__)

PORTS_JSON = Path(__file__).parent / "ports.json"


def _port_to_rtree_id(code: str) -> int:
    """Hash port code to a stable integer for R*Tree id."""
    return int(hashlib.md5(code.encode()).hexdigest()[:15], 16)


async def load_ports(db: aiosqlite.Connection):
    """Load ports from bundled JSON into SQLite (idempotent)."""
    # Check if already loaded
    async with db.execute("SELECT COUNT(*) FROM ports") as cursor:
        count = (await cursor.fetchone())[0]
        if count > 0:
            logger.info("Ports already loaded (%d ports)", count)
            return

    if not PORTS_JSON.exists():
        logger.warning("ports.json not found at %s", PORTS_JSON)
        return

    with open(PORTS_JSON, "r") as f:
        ports = json.load(f)

    await db.executemany(
        """
        INSERT OR IGNORE INTO ports (code, name, country, latitude, longitude, port_type, size)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (p["code"], p["name"], p.get("country"), p["latitude"], p["longitude"],
             p.get("port_type"), p.get("size"))
            for p in ports
        ],
    )

    # Populate R*Tree
    for p in ports:
        rtree_id = _port_to_rtree_id(p["code"])
        await db.execute(
            "INSERT OR REPLACE INTO ports_rtree (id, min_lat, max_lat, min_lon, max_lon) VALUES (?, ?, ?, ?, ?)",
            (rtree_id, p["latitude"], p["latitude"], p["longitude"], p["longitude"]),
        )

    await db.commit()
    logger.info("Loaded %d ports into database", len(ports))


async def get_ports_near(db: aiosqlite.Connection, lat: float, lon: float, radius_km: float = 50, max_results: int = 20) -> list[dict]:
    """Find ports near a location using bounding box filter."""
    delta = radius_km / 111.0
    async with db.execute(
        """
        SELECT * FROM ports
        WHERE latitude BETWEEN ? AND ?
          AND longitude BETWEEN ? AND ?
        ORDER BY ABS(latitude - ?) + ABS(longitude - ?) ASC
        LIMIT ?
        """,
        (lat - delta, lat + delta, lon - delta, lon + delta, lat, lon, max_results),
    ) as cursor:
        rows = await cursor.fetchall()
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row)) for row in rows]


async def get_port_by_code(db: aiosqlite.Connection, code: str) -> dict | None:
    """Get a port by UN/LOCODE."""
    async with db.execute("SELECT * FROM ports WHERE code = ?", (code.strip().upper(),)) as cursor:
        row = await cursor.fetchone()
        if not row:
            return None
        columns = [d[0] for d in cursor.description]
        return dict(zip(columns, row))

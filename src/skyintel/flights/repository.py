"""SQLite flight cache — insert, query by bbox, prune old data."""

import aiosqlite
from datetime import datetime, timezone, timedelta
from dataclasses import asdict
from skyintel.models import NormalizedFlight

RETENTION_HOURS = 24


async def insert_flights(db: aiosqlite.Connection, flights: list[NormalizedFlight]):
    """Batch insert flights into cache."""
    if not flights:
        return
    await db.executemany(
        """
        INSERT INTO flights (
            icao24, callsign, aircraft_type, model, operator, registration,
            origin, destination, latitude, longitude, altitude_m,
            velocity_ms, heading, vertical_rate, squawk, timestamp
        ) VALUES (
            :icao24, :callsign, :aircraft_type, :model, :operator, :registration,
            :origin, :destination, :latitude, :longitude, :altitude_m,
            :velocity_ms, :heading, :vertical_rate, :squawk, :timestamp
        )
        """,
        [asdict(f) for f in flights],
    )
    await db.commit()


async def get_latest_flights(
    db: aiosqlite.Connection,
    lat_min: float = -90, lat_max: float = 90,
    lon_min: float = -180, lon_max: float = 180,
) -> list[dict]:
    """Get the most recent position for each aircraft within a bounding box."""
    query = """
        SELECT *, MAX(timestamp) as latest
        FROM flights
        WHERE latitude BETWEEN ? AND ?
          AND longitude BETWEEN ? AND ?
          AND timestamp >= ?
        GROUP BY icao24
        ORDER BY aircraft_type = 'military' DESC, callsign
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    async with db.execute(query, (lat_min, lat_max, lon_min, lon_max, cutoff)) as cursor:
        rows = await cursor.fetchall()
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row)) for row in rows]


async def prune_old_flights(db: aiosqlite.Connection):
    """Remove flights older than retention period."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=RETENTION_HOURS)).isoformat()
    await db.execute("DELETE FROM flights WHERE timestamp < ?", (cutoff,))
    await db.commit()

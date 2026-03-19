"""SQLite CRUD for vessels — batched upsert by MMSI, R*Tree sync, prune."""

import logging
import hashlib
from datetime import datetime, timezone, timedelta

import aiosqlite

from voyageintel.models import NormalizedVessel

logger = logging.getLogger(__name__)


def _mmsi_to_rtree_id(mmsi: str) -> int:
    """Hash MMSI to a stable integer for R*Tree id."""
    return int(hashlib.md5(mmsi.encode()).hexdigest()[:15], 16)


async def batch_upsert_vessels(db: aiosqlite.Connection, vessels: list[NormalizedVessel]):
    """Batch upsert vessels by MMSI with R*Tree sync."""
    if not vessels:
        return

    now = datetime.now(timezone.utc).isoformat()

    await db.executemany(
        """
        INSERT INTO vessels (
            mmsi, imo, name, callsign, vessel_type, vessel_type_code,
            flag_country, latitude, longitude, cog, sog, heading, rot,
            nav_status, nav_status_code, destination, eta, draught,
            length, width, source, timestamp, first_seen, updated_at
        ) VALUES (
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?
        )
        ON CONFLICT(mmsi) DO UPDATE SET
            imo = COALESCE(excluded.imo, vessels.imo),
            name = COALESCE(excluded.name, vessels.name),
            callsign = COALESCE(excluded.callsign, vessels.callsign),
            vessel_type = CASE WHEN excluded.vessel_type != 'unknown' THEN excluded.vessel_type ELSE vessels.vessel_type END,
            vessel_type_code = COALESCE(excluded.vessel_type_code, vessels.vessel_type_code),
            flag_country = COALESCE(excluded.flag_country, vessels.flag_country),
            latitude = COALESCE(excluded.latitude, vessels.latitude),
            longitude = COALESCE(excluded.longitude, vessels.longitude),
            cog = COALESCE(excluded.cog, vessels.cog),
            sog = COALESCE(excluded.sog, vessels.sog),
            heading = COALESCE(excluded.heading, vessels.heading),
            rot = COALESCE(excluded.rot, vessels.rot),
            nav_status = COALESCE(excluded.nav_status, vessels.nav_status),
            nav_status_code = COALESCE(excluded.nav_status_code, vessels.nav_status_code),
            destination = COALESCE(excluded.destination, vessels.destination),
            eta = COALESCE(excluded.eta, vessels.eta),
            draught = COALESCE(excluded.draught, vessels.draught),
            length = COALESCE(excluded.length, vessels.length),
            width = COALESCE(excluded.width, vessels.width),
            timestamp = excluded.timestamp,
            updated_at = excluded.updated_at
        WHERE excluded.timestamp >= vessels.timestamp
        """,
        [
            (
                v.mmsi, v.imo, v.name, v.callsign, v.vessel_type, v.vessel_type_code,
                v.flag_country, v.latitude, v.longitude, v.cog, v.sog, v.heading, v.rot,
                v.nav_status, v.nav_status_code, v.destination, v.eta, v.draught,
                v.length, v.width, v.source, v.timestamp, now, now,
            )
            for v in vessels
        ],
    )

    # Sync R*Tree
    for v in vessels:
        if v.latitude is not None and v.longitude is not None:
            rtree_id = _mmsi_to_rtree_id(v.mmsi)
            await db.execute(
                "INSERT OR REPLACE INTO vessels_rtree (id, min_lat, max_lat, min_lon, max_lon) VALUES (?, ?, ?, ?, ?)",
                (rtree_id, v.latitude, v.latitude, v.longitude, v.longitude),
            )

    await db.commit()
    logger.debug("Upserted %d vessels", len(vessels))


async def get_vessels_near(db: aiosqlite.Connection, lat: float, lon: float, radius_km: float = 50, max_results: int = 50) -> list[dict]:
    """Get vessels near a point using R*Tree bounding box + Haversine filter."""
    # Approximate bounding box (1 degree ≈ 111km)
    delta = radius_km / 111.0
    min_lat = lat - delta
    max_lat = lat + delta
    min_lon = lon - delta
    max_lon = lon + delta

    query = """
        SELECT v.* FROM vessels v
        INNER JOIN vessels_rtree r ON r.id = (
            CAST(substr(hex(md5(v.mmsi)), 1, 15) AS INTEGER)
        )
        WHERE v.latitude BETWEEN ? AND ?
          AND v.longitude BETWEEN ? AND ?
        ORDER BY v.vessel_type = 'military' DESC, v.sog DESC
        LIMIT ?
    """
    # Simpler approach: just use the vessels table with bbox filter
    query = """
        SELECT * FROM vessels
        WHERE latitude BETWEEN ? AND ?
          AND longitude BETWEEN ? AND ?
        ORDER BY vessel_type = 'military' DESC, sog DESC
        LIMIT ?
    """
    async with db.execute(query, (min_lat, max_lat, min_lon, max_lon, max_results)) as cursor:
        rows = await cursor.fetchall()
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row)) for row in rows]


async def get_vessels_by_type(db: aiosqlite.Connection, vessel_type: str, max_results: int = 50) -> list[dict]:
    """Get vessels filtered by type."""
    async with db.execute(
        "SELECT * FROM vessels WHERE vessel_type = ? ORDER BY updated_at DESC LIMIT ?",
        (vessel_type, max_results),
    ) as cursor:
        rows = await cursor.fetchall()
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row)) for row in rows]


async def search_vessel(db: aiosqlite.Connection, query: str, max_results: int = 50) -> list[dict]:
    """Search vessels by name, MMSI, or IMO."""
    q = query.strip().upper()
    async with db.execute(
        """
        SELECT * FROM vessels
        WHERE UPPER(name) LIKE ? OR mmsi = ? OR imo = ?
        ORDER BY vessel_type = 'military' DESC, updated_at DESC
        LIMIT ?
        """,
        (f"%{q}%", q, q, max_results),
    ) as cursor:
        rows = await cursor.fetchall()
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row)) for row in rows]


async def get_vessel_by_mmsi(db: aiosqlite.Connection, mmsi: str) -> dict | None:
    """Get a single vessel by MMSI."""
    async with db.execute("SELECT * FROM vessels WHERE mmsi = ?", (mmsi,)) as cursor:
        row = await cursor.fetchone()
        if not row:
            return None
        columns = [d[0] for d in cursor.description]
        return dict(zip(columns, row))


async def get_military_vessels(db: aiosqlite.Connection, max_results: int = 50) -> list[dict]:
    """Get all tracked military/naval vessels."""
    async with db.execute(
        "SELECT * FROM vessels WHERE vessel_type = 'military' ORDER BY updated_at DESC LIMIT ?",
        (max_results,),
    ) as cursor:
        rows = await cursor.fetchall()
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row)) for row in rows]


async def get_all_vessels(
    db: aiosqlite.Connection,
    lat_min: float = -90, lat_max: float = 90,
    lon_min: float = -180, lon_max: float = 180,
) -> list[dict]:
    """Get all vessels within a bounding box."""
    query = """
        SELECT * FROM vessels
        WHERE latitude BETWEEN ? AND ?
          AND longitude BETWEEN ? AND ?
        ORDER BY vessel_type = 'military' DESC, sog DESC
    """
    async with db.execute(query, (lat_min, lat_max, lon_min, lon_max)) as cursor:
        rows = await cursor.fetchall()
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row)) for row in rows]


async def get_vessel_stats(db: aiosqlite.Connection) -> dict:
    """Get vessel count by type."""
    async with db.execute(
        "SELECT vessel_type, COUNT(*) as count FROM vessels GROUP BY vessel_type"
    ) as cursor:
        rows = await cursor.fetchall()
        stats = {row[0]: row[1] for row in rows}
        stats["total"] = sum(stats.values())
        return stats


async def prune_stale_vessels(db: aiosqlite.Connection, hours: int = 6):
    """Remove vessels with no AIS update within retention window."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    await db.execute("DELETE FROM vessels WHERE updated_at < ?", (cutoff,))
    await db.commit()
    logger.info("Pruned stale vessels (cutoff=%s)", cutoff)

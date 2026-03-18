"""SQLite TLE cache for satellites."""

import aiosqlite
from datetime import datetime, timezone


async def upsert_satellites(db: aiosqlite.Connection, satellites: list[dict]):
    """Insert or update TLEs in cache."""
    if not satellites:
        return
    now = datetime.now(timezone.utc).isoformat()
    await db.executemany(
        """
        INSERT INTO satellites (norad_id, name, category, tle_line1, tle_line2, epoch, updated_at)
        VALUES (:norad_id, :name, :category, :tle_line1, :tle_line2, '', :updated_at)
        ON CONFLICT(norad_id) DO UPDATE SET
            name = excluded.name,
            category = excluded.category,
            tle_line1 = excluded.tle_line1,
            tle_line2 = excluded.tle_line2,
            updated_at = excluded.updated_at
        """,
        [{**s, "updated_at": now} for s in satellites],
    )
    await db.commit()


async def get_satellites_by_category(db: aiosqlite.Connection, category: str | None = None) -> list[dict]:
    """Get cached TLEs, optionally filtered by category."""
    if category:
        query = "SELECT norad_id, name, category, tle_line1, tle_line2 FROM satellites WHERE category = ?"
        params = (category,)
    else:
        query = "SELECT norad_id, name, category, tle_line1, tle_line2 FROM satellites"
        params = ()

    async with db.execute(query, params) as cursor:
        rows = await cursor.fetchall()
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row)) for row in rows]


async def get_satellite_by_norad(db: aiosqlite.Connection, norad_id: int) -> dict | None:
    """Get a single satellite by NORAD ID."""
    async with db.execute(
        "SELECT norad_id, name, category, tle_line1, tle_line2 FROM satellites WHERE norad_id = ?",
        (norad_id,),
    ) as cursor:
        row = await cursor.fetchone()
        if not row:
            return None
        columns = [d[0] for d in cursor.description]
        return dict(zip(columns, row))

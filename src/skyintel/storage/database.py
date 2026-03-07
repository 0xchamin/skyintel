import aiosqlite
from pathlib import Path

_db: aiosqlite.Connection | None = None


async def get_db(db_path: Path) -> aiosqlite.Connection:
    """Get or create a singleton database connection with WAL mode and foreign keys."""
    global _db
    if _db is None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _db = await aiosqlite.connect(db_path)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
    return _db


async def close_db():
    """Close the database connection."""
    global _db
    if _db is not None:
        await _db.close()
        _db = None

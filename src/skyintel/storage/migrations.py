import aiosqlite


SCHEMA_VERSION = 2

MIGRATIONS = {
    1: [
        # --- Flights ---
        """
        CREATE TABLE IF NOT EXISTS flights (
            icao24          TEXT NOT NULL,
            callsign        TEXT,
            aircraft_type   TEXT,
            model           TEXT,
            operator        TEXT,
            registration    TEXT,
            origin          TEXT,
            destination     TEXT,
            latitude        REAL,
            longitude       REAL,
            altitude_m      REAL,
            velocity_ms     REAL,
            heading         REAL,
            vertical_rate   REAL,
            squawk          TEXT,
            timestamp       TEXT NOT NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_flights_timestamp ON flights (timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_flights_icao24 ON flights (icao24)",
        "CREATE INDEX IF NOT EXISTS idx_flights_position ON flights (latitude, longitude)",

        # --- Satellites ---
        """
        CREATE TABLE IF NOT EXISTS satellites (
            norad_id    INTEGER PRIMARY KEY,
            name        TEXT NOT NULL,
            category    TEXT,
            tle_line1   TEXT NOT NULL,
            tle_line2   TEXT NOT NULL,
            epoch       TEXT,
            updated_at  TEXT NOT NULL
        )
        """,

        # --- Alerts ---
        """
        CREATE TABLE IF NOT EXISTS alerts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            zone_type   TEXT NOT NULL,
            zone_data   TEXT NOT NULL,
            trigger     TEXT NOT NULL,
            notify      TEXT NOT NULL DEFAULT 'browser',
            active      INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT NOT NULL
        )
        """,

        # --- Alert History ---
        """
        CREATE TABLE IF NOT EXISTS alert_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_id    INTEGER NOT NULL,
            matched     TEXT NOT NULL,
            triggered_at TEXT NOT NULL,
            FOREIGN KEY (alert_id) REFERENCES alerts(id) ON DELETE CASCADE
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_alert_history_alert_id ON alert_history (alert_id)",

        # --- Schema version tracking ---
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER NOT NULL
        )
        """,
        "INSERT INTO schema_version (version) VALUES (1)",
    ],
    2: [
        """
        CREATE TABLE IF NOT EXISTS aircraft_meta (
            icao24          TEXT PRIMARY KEY,
            registration    TEXT,
            manufacturer    TEXT,
            type_code       TEXT,
            type_name       TEXT,
            owner           TEXT,
            operator_code   TEXT,
            updated_at      TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS routes (
            callsign        TEXT PRIMARY KEY,
            origin_icao     TEXT,
            destination_icao TEXT,
            updated_at      TEXT NOT NULL
        )
        """,
        "UPDATE schema_version SET version = 2",
    ],

}


async def get_current_version(db: aiosqlite.Connection) -> int:
    """Get the current schema version, or 0 if no schema exists."""
    try:
        async with db.execute("SELECT version FROM schema_version LIMIT 1") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
    except aiosqlite.OperationalError:
        return 0


async def run_migrations(db: aiosqlite.Connection):
    """Run all pending migrations."""
    current = await get_current_version(db)
    for version in range(current + 1, SCHEMA_VERSION + 1):
        if version in MIGRATIONS:
            for sql in MIGRATIONS[version]:
                await db.execute(sql)
            await db.execute("UPDATE schema_version SET version = ?", (version,))
    await db.commit()

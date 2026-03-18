import aiosqlite


SCHEMA_VERSION = 3

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
    3: [
        # --- Vessels ---
        """
        CREATE TABLE IF NOT EXISTS vessels (
            mmsi            TEXT PRIMARY KEY,
            imo             TEXT,
            name            TEXT,
            callsign        TEXT,
            vessel_type     TEXT,
            vessel_type_code INTEGER,
            flag_country    TEXT,
            latitude        REAL,
            longitude       REAL,
            cog             REAL,
            sog             REAL,
            heading         REAL,
            rot             REAL,
            nav_status      TEXT,
            nav_status_code INTEGER,
            destination     TEXT,
            eta             TEXT,
            draught         REAL,
            length          REAL,
            width           REAL,
            source          TEXT DEFAULT 'aisstream',
            timestamp       TEXT NOT NULL,
            first_seen      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_vessels_type ON vessels (vessel_type)",
        "CREATE INDEX IF NOT EXISTS idx_vessels_timestamp ON vessels (updated_at)",
        "CREATE INDEX IF NOT EXISTS idx_vessels_destination ON vessels (destination)",
        "CREATE INDEX IF NOT EXISTS idx_vessels_flag ON vessels (flag_country)",

        # --- Vessels R*Tree spatial index ---
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS vessels_rtree USING rtree(
            id,
            min_lat, max_lat,
            min_lon, max_lon
        )
        """,

        # --- Ports ---
        """
        CREATE TABLE IF NOT EXISTS ports (
            code            TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            country         TEXT,
            latitude        REAL NOT NULL,
            longitude       REAL NOT NULL,
            port_type       TEXT,
            size            TEXT
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_ports_country ON ports (country)",

        # --- Ports R*Tree spatial index ---
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS ports_rtree USING rtree(
            id,
            min_lat, max_lat,
            min_lon, max_lon
        )
        """,

        # --- Vessel metadata cache ---
        """
        CREATE TABLE IF NOT EXISTS vessel_meta (
            mmsi            TEXT PRIMARY KEY,
            photo_url       TEXT,
            owner           TEXT,
            operator        TEXT,
            built_year      INTEGER,
            gross_tonnage   INTEGER,
            deadweight      INTEGER,
            cached_at       TEXT NOT NULL
        )
        """,

        # --- Geocode cache ---
        """
        CREATE TABLE IF NOT EXISTS geocode_cache (
            place_name      TEXT PRIMARY KEY,
            latitude        REAL NOT NULL,
            longitude       REAL NOT NULL,
            formatted_addr  TEXT,
            cached_at       TEXT NOT NULL
        )
        """,

        "UPDATE schema_version SET version = 3",
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

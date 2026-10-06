"""TagForge SQLite schema — the seven tables from the design doc, Figure 1.

Run directly to create (or check) tagforge.db in the project root:
    python -m tagforge.db.sqlite

Groups:
    Main records : Project, Controller, Tag
    Lookups      : DataType, EquipmentArea
    Import audit : ImportBatch, ImportError
"""
import sqlite3

from pathlib import Path
from .connection import get_connection, DB_PATH

# Bump this when the schema changes, and add a migration step in init_schema().
SCHEMA_VERSION = 1



# ISO-8601 UTC, e.g. 2026-10-03T18:45:00Z — used as the default for timestamp columns.
NOW_UTC = "(strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))"


SCHEMA = f"""
-- ============================================================ Main records

CREATE TABLE IF NOT EXISTS Project (
    project_id    INTEGER PRIMARY KEY,            -- alias for rowid: auto-assigned
    project_name  TEXT    NOT NULL UNIQUE,        -- unique across the whole database
    site_label    TEXT,
    description   TEXT,
    created_utc   TEXT    NOT NULL DEFAULT {NOW_UTC},
    updated_utc   TEXT    NOT NULL DEFAULT {NOW_UTC}
);

CREATE TABLE IF NOT EXISTS Controller (
    controller_id   INTEGER PRIMARY KEY,
    project_id      INTEGER NOT NULL
                    REFERENCES Project (project_id) ON DELETE CASCADE,   -- composition
    controller_name TEXT    NOT NULL,
    make            TEXT,
    model           TEXT,
    address_note    TEXT,
    created_utc     TEXT    NOT NULL DEFAULT {NOW_UTC},
    updated_utc     TEXT    NOT NULL DEFAULT {NOW_UTC},
    UNIQUE (project_id, controller_name)          -- unique within a project only
);

-- ============================================================ Lookups

CREATE TABLE IF NOT EXISTS DataType (
    data_type_id  INTEGER PRIMARY KEY,
    type_name     TEXT    NOT NULL UNIQUE,
    category      TEXT,
    is_numeric    INTEGER NOT NULL DEFAULT 0 CHECK (is_numeric IN (0, 1))
);

CREATE TABLE IF NOT EXISTS EquipmentArea (
    area_id       INTEGER PRIMARY KEY,
    project_id    INTEGER NOT NULL
                  REFERENCES Project (project_id) ON DELETE CASCADE,
    area_name     TEXT    NOT NULL,
    description   TEXT,
    UNIQUE (project_id, area_name)
);

-- ============================================================ Tag

-- Lookup FKs (data_type_id, area_id) use the default NO ACTION rather than
-- RESTRICT. Both block deleting a lookup that a tag still uses, but NO ACTION
-- is checked at the END of the statement. That matters when a Project is
-- deleted: its EquipmentAreas and its Controllers->Tags cascade in the same
-- statement, and RESTRICT could fire on an area before its tags are gone.
CREATE TABLE IF NOT EXISTS Tag (
    tag_id          INTEGER PRIMARY KEY,
    controller_id   INTEGER NOT NULL
                    REFERENCES Controller (controller_id) ON DELETE CASCADE,
    data_type_id    INTEGER NOT NULL
                    REFERENCES DataType (data_type_id),
    area_id         INTEGER
                    REFERENCES EquipmentArea (area_id),               -- nullable
    tag_name        TEXT    NOT NULL,
    description     TEXT,
    address_path    TEXT,
    eng_units       TEXT,
    raw_min         REAL,
    raw_max         REAL,
    eu_min          REAL,
    eu_max          REAL,
    alarm_enabled   INTEGER NOT NULL DEFAULT 0 CHECK (alarm_enabled IN (0, 1)),
    alarm_lo        REAL,
    alarm_hi        REAL,
    alarm_priority  TEXT,
    notes           TEXT,
    created_utc     TEXT    NOT NULL DEFAULT {NOW_UTC},
    updated_utc     TEXT    NOT NULL DEFAULT {NOW_UTC},

    UNIQUE (controller_id, tag_name),

    -- NAME_PATTERN: non-empty, only A-Z, 0-9 and underscore.
    -- GLOB is case-sensitive, so lowercase letters are rejected too.
    CHECK (tag_name <> '' AND tag_name NOT GLOB '*[^A-Z0-9_]*'),

    -- SCALE_ORDER: only checked when both ends are filled in
    -- (NULL = "not used", e.g. BOOL and STRING tags).
    CHECK (eu_min  IS NULL OR eu_max  IS NULL OR eu_min  < eu_max),
    CHECK (raw_min IS NULL OR raw_max IS NULL OR raw_min < raw_max),
    CHECK (alarm_lo IS NULL OR alarm_hi IS NULL OR alarm_lo < alarm_hi)

    -- Not enforced here (application code only): ALARM_RANGE (alarm inside the
    -- EU span), "scaling required for numeric types", and "area belongs to the
    -- same project as the controller". These feed TF-R02's enforcement map.
);

-- ============================================================ Import audit

CREATE TABLE IF NOT EXISTS ImportBatch (
    batch_id       INTEGER PRIMARY KEY,
    project_id     INTEGER NOT NULL
                   REFERENCES Project (project_id) ON DELETE CASCADE,
    -- Target controller. SET NULL keeps the history if the controller is deleted.
    controller_id  INTEGER
                   REFERENCES Controller (controller_id) ON DELETE SET NULL,
    source_file    TEXT    NOT NULL,
    imported_utc   TEXT    NOT NULL DEFAULT {NOW_UTC},
    rows_read      INTEGER NOT NULL DEFAULT 0 CHECK (rows_read     >= 0),
    rows_accepted  INTEGER NOT NULL DEFAULT 0 CHECK (rows_accepted >= 0),
    rows_rejected  INTEGER NOT NULL DEFAULT 0 CHECK (rows_rejected >= 0),
    committed      INTEGER NOT NULL DEFAULT 0 CHECK (committed IN (0, 1))  -- TF-R02 disposition
);

CREATE TABLE IF NOT EXISTS ImportError (
    error_id        INTEGER PRIMARY KEY,
    batch_id        INTEGER NOT NULL
                    REFERENCES ImportBatch (batch_id) ON DELETE CASCADE,
    row_number      INTEGER,
    column_name     TEXT,
    offending_value TEXT,
    rule_code       TEXT    NOT NULL,
    message         TEXT    NOT NULL
);

-- ============================================================ Indexes
-- (controller_id, tag_name) is already indexed by its UNIQUE constraint.

CREATE INDEX IF NOT EXISTS idx_tag_area      ON Tag (area_id);
CREATE INDEX IF NOT EXISTS idx_tag_data_type ON Tag (data_type_id);
CREATE INDEX IF NOT EXISTS idx_tag_name      ON Tag (tag_name);
CREATE INDEX IF NOT EXISTS idx_batch_project ON ImportBatch (project_id);
CREATE INDEX IF NOT EXISTS idx_error_batch   ON ImportError (batch_id);
"""

# (type_name, category, is_numeric)
DATA_TYPES = [
    ('BOOL',    'discrete',  0),
    ('INT',     'numeric',   1),
    ('DINT',    'numeric',   1),
    ('REAL',    'numeric',   1),
    ('STRING',  'text',      0),
    ('TIMER',   'structure', 0),
    ('COUNTER', 'structure', 0),
]





def init_schema(conn: sqlite3.Connection) -> int:
    """Create the schema and seed lookups if needed. Returns the schema version.

    The version lives in SQLite's built-in PRAGMA user_version (0 = new file).
    """
    current = conn.execute('PRAGMA user_version').fetchone()[0]

    if current > SCHEMA_VERSION:
        raise RuntimeError(
            f'Database schema v{current} is newer than this app supports '
            f'(v{SCHEMA_VERSION}). Update TagForge before opening this file.')

    if current == SCHEMA_VERSION:
        return current

    if current == 0:
        # One transaction: either the whole schema + seed lands, or nothing does.
        with conn:
            conn.executescript('BEGIN;' + SCHEMA)
            conn.executemany(
                'INSERT OR IGNORE INTO DataType (type_name, category, is_numeric) '
                'VALUES (?, ?, ?)', DATA_TYPES)
            conn.execute(f'PRAGMA user_version = {SCHEMA_VERSION}')

    # Future: elif current == 1: migrate 1 -> 2 (back up the file first).

    return conn.execute('PRAGMA user_version').fetchone()[0]


if __name__ == '__main__':
    conn = get_connection()
    try:
        version = init_schema(conn)
        tables = [r['name'] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        print(f'{DB_PATH}  schema v{version}')
        print('tables:', ', '.join(tables))
    finally:
        conn.close()

import sqlite3

from airguard.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    lat         REAL,
    lon         REAL,
    diagnosis   TEXT,
    allergens   TEXT,
    pm25_threshold  REAL DEFAULT 25.0,
    pm10_threshold  REAL DEFAULT 50.0,
    no2_threshold   REAL DEFAULT 40.0,
    o3_threshold    REAL DEFAULT 100.0,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS measurements (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(user_id),
    pm25        REAL,
    pm10        REAL,
    no2         REAL,
    o3          REAL,
    pollen_tree  REAL,
    pollen_grass REAL,
    uv_index    REAL,
    score       REAL,
    risk_level  TEXT,
    alert_type  TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);
"""


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()

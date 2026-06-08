"""SQLite storage for tag selections and location history."""
from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from . import config
from .findmy import TagLocation


SCHEMA = """
CREATE TABLE IF NOT EXISTS selections (
    device_id TEXT PRIMARY KEY,
    name      TEXT NOT NULL,
    selected  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS locations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id   TEXT    NOT NULL,
    name        TEXT,
    latitude    REAL    NOT NULL,
    longitude   REAL    NOT NULL,
    accuracy    REAL,
    timestamp   INTEGER,              -- fix time from Find My (epoch ms)
    recorded_at INTEGER NOT NULL      -- when we sampled it (epoch ms)
);

CREATE INDEX IF NOT EXISTS idx_locations_device
    ON locations (device_id, recorded_at);
"""


def _connect(path: Optional[Path] = None) -> sqlite3.Connection:
    path = path or config.DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_conn(path: Optional[Path] = None) -> Iterator[sqlite3.Connection]:
    conn = _connect(path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(path: Optional[Path] = None) -> None:
    with get_conn(path) as conn:
        conn.executescript(SCHEMA)


# --- selections ----------------------------------------------------------

def set_selected(device_id: str, name: str, selected: bool) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO selections (device_id, name, selected)
            VALUES (?, ?, ?)
            ON CONFLICT(device_id) DO UPDATE SET
                name = excluded.name,
                selected = excluded.selected
            """,
            (device_id, name, 1 if selected else 0),
        )


def get_selected_ids() -> set[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT device_id FROM selections WHERE selected = 1"
        ).fetchall()
    return {row["device_id"] for row in rows}


def get_selection_map() -> dict[str, bool]:
    with get_conn() as conn:
        rows = conn.execute("SELECT device_id, selected FROM selections").fetchall()
    return {row["device_id"]: bool(row["selected"]) for row in rows}


# --- locations -----------------------------------------------------------

def record_location(tag: TagLocation) -> bool:
    """Persist a location fix for a tag.

    Skips insertion when the newest stored fix has the same Find My timestamp,
    so we don't store duplicate points when a tag hasn't moved/reported.
    Returns True if a row was inserted.
    """
    if not tag.has_location():
        return False

    with get_conn() as conn:
        last = conn.execute(
            """
            SELECT timestamp FROM locations
            WHERE device_id = ?
            ORDER BY recorded_at DESC
            LIMIT 1
            """,
            (tag.device_id,),
        ).fetchone()

        if last is not None and tag.timestamp is not None and last["timestamp"] == tag.timestamp:
            return False

        conn.execute(
            """
            INSERT INTO locations
                (device_id, name, latitude, longitude, accuracy, timestamp, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tag.device_id,
                tag.name,
                tag.latitude,
                tag.longitude,
                tag.accuracy,
                tag.timestamp,
                int(time.time() * 1000),
            ),
        )
    return True


def get_track(device_id: str, limit: int = 1000) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT device_id, name, latitude, longitude, accuracy, timestamp, recorded_at
            FROM locations
            WHERE device_id = ?
            ORDER BY recorded_at ASC
            LIMIT ?
            """,
            (device_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]

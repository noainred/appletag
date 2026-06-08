"""Application configuration.

Values can be overridden with environment variables, which is handy for
development (e.g. pointing at a sample data file instead of the real
FindMy cache) and for tweaking the polling interval.
"""
import os
from pathlib import Path

# Default location of the FindMy "items" cache on macOS. This file is written
# by the Find My app and contains the last known location of every AirTag /
# Find My accessory registered to the signed-in Apple ID.
DEFAULT_ITEMS_PATH = (
    Path.home()
    / "Library"
    / "Caches"
    / "com.apple.findmy.fmipcore"
    / "Items.data"
)

# Path to the FindMy items cache. Override with APPLETAG_ITEMS_PATH to point at
# a sample file when developing on a non-Mac machine.
ITEMS_PATH = Path(os.environ.get("APPLETAG_ITEMS_PATH", str(DEFAULT_ITEMS_PATH)))

# SQLite database file that stores the tracking history.
DB_PATH = Path(
    os.environ.get("APPLETAG_DB_PATH", str(Path(__file__).resolve().parent.parent / "tracking.db"))
)

# How often (in seconds) to sample the location of selected tags.
# Defaults to 5 minutes as requested.
POLL_INTERVAL_SECONDS = int(os.environ.get("APPLETAG_POLL_INTERVAL", str(5 * 60)))

# Host / port for the web server.
HOST = os.environ.get("APPLETAG_HOST", "127.0.0.1")
PORT = int(os.environ.get("APPLETAG_PORT", "8000"))

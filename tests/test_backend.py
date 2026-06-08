"""Tests for the AppleTag tracker backend.

Run with: pytest -q
These use the bundled sample data and a temporary database, so they do not
require a Mac or the real Find My cache.
"""
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "sample" / "Items.data"


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """Point config at the sample data + a throwaway DB, then reload modules."""
    monkeypatch.setenv("APPLETAG_ITEMS_PATH", str(SAMPLE))
    monkeypatch.setenv("APPLETAG_DB_PATH", str(tmp_path / "test.db"))

    import importlib
    from backend import config, database, findmy

    importlib.reload(config)
    importlib.reload(findmy)
    importlib.reload(database)
    database.init_db()
    return database, findmy


def test_read_items_parses_sample(env):
    _, findmy = env
    items = findmy.read_items()
    assert len(items) == 3
    names = {i.name for i in items}
    assert {"열쇠고리", "백팩", "지갑"} == names
    for item in items:
        assert item.has_location()
        assert item.device_id


def test_record_dedup(env):
    database, findmy = env
    item = findmy.read_items()[0]
    assert database.record_location(item) is True
    # Same Find My timestamp -> no duplicate row.
    assert database.record_location(item) is False
    track = database.get_track(item.device_id)
    assert len(track) == 1


def test_selection_roundtrip(env):
    database, findmy = env
    item = findmy.read_items()[0]
    database.set_selected(item.device_id, item.name, True)
    assert item.device_id in database.get_selected_ids()
    database.set_selected(item.device_id, item.name, False)
    assert item.device_id not in database.get_selected_ids()


def test_missing_cache_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("APPLETAG_ITEMS_PATH", str(tmp_path / "nope.data"))
    import importlib
    from backend import config, findmy

    importlib.reload(config)
    importlib.reload(findmy)
    with pytest.raises(FileNotFoundError):
        findmy.read_items()


def test_api_endpoints(env):
    """Smoke-test the FastAPI app end-to-end with TestClient."""
    import importlib
    from fastapi.testclient import TestClient
    from backend import app as app_module

    importlib.reload(app_module)
    with TestClient(app_module.app) as client:
        devices = client.get("/api/devices").json()
        assert len(devices) == 3
        target = devices[0]["device_id"]

        r = client.post("/api/select", json={"device_id": target, "selected": True})
        assert r.status_code == 200

        r = client.post("/api/poll-now").json()
        assert r["inserted"] == 1

        track = client.get(f"/api/track/{target}").json()
        assert len(track) == 1

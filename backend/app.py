"""FastAPI application: REST API + static web frontend."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, database, findmy, scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    task = asyncio.create_task(scheduler.run_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="AppleTag Tracker", lifespan=lifespan)


class SelectRequest(BaseModel):
    device_id: str
    selected: bool


@app.get("/api/devices")
def list_devices():
    """List every Find My item with its selection state and current location."""
    try:
        items = findmy.read_items()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"FindMy 캐시 파싱 실패: {exc}")

    selection = database.get_selection_map()
    result = []
    for item in items:
        d = item.to_dict()
        d["selected"] = selection.get(item.device_id, False)
        result.append(d)
    return result


@app.post("/api/select")
def select_device(req: SelectRequest):
    """Mark a tag as tracked / not tracked."""
    item = findmy.get_item(req.device_id)
    if item is None:
        raise HTTPException(status_code=404, detail="해당 기기를 찾을 수 없습니다.")
    database.set_selected(req.device_id, item.name, req.selected)
    return {"device_id": req.device_id, "selected": req.selected}


@app.get("/api/track/{device_id}")
def get_track(device_id: str, limit: int = 1000):
    """Return the recorded location history for one tag."""
    return database.get_track(device_id, limit=limit)


@app.post("/api/poll-now")
async def poll_now():
    """Trigger an immediate sample of all selected tags."""
    inserted = await scheduler.poll_once()
    return {"inserted": inserted}


@app.get("/api/health")
def health():
    return JSONResponse(
        {
            "items_path": str(config.ITEMS_PATH),
            "items_path_exists": config.ITEMS_PATH.exists(),
            "poll_interval_seconds": config.POLL_INTERVAL_SECONDS,
        }
    )


# Serve the frontend (index.html, app.js, style.css) at the root.
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

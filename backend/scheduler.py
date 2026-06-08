"""Background poller that samples selected tags every N minutes."""
from __future__ import annotations

import asyncio
import logging

from . import config, database, findmy

log = logging.getLogger("appletag.scheduler")


async def poll_once() -> int:
    """Sample all currently selected tags once. Returns rows inserted."""
    selected = database.get_selected_ids()
    if not selected:
        return 0

    try:
        items = findmy.read_items()
    except FileNotFoundError as exc:
        log.warning("FindMy 캐시를 읽을 수 없습니다: %s", exc)
        return 0
    except Exception:  # noqa: BLE001 - never let the loop die
        log.exception("FindMy 캐시 파싱 실패")
        return 0

    inserted = 0
    for item in items:
        if item.device_id in selected and database.record_location(item):
            inserted += 1
            log.info("기록: %s @ (%s, %s)", item.name, item.latitude, item.longitude)
    return inserted


async def run_loop() -> None:
    """Run poll_once() forever on the configured interval."""
    interval = config.POLL_INTERVAL_SECONDS
    log.info("위치 추적 시작: %d초마다 폴링", interval)
    while True:
        try:
            await poll_once()
        except asyncio.CancelledError:
            log.info("위치 추적 중지")
            raise
        except Exception:  # noqa: BLE001
            log.exception("폴링 루프 오류")
        await asyncio.sleep(interval)

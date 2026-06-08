"""Read and parse the macOS FindMy items cache.

Apple does not provide a public API for AirTag locations. However, on a Mac
that is signed into the same Apple ID as the AirTags, the Find My app keeps a
JSON cache of the last known location of every item at::

    ~/Library/Caches/com.apple.findmy.fmipcore/Items.data

This module reads that file and normalises each entry into a small, stable
dict that the rest of the app can rely on.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

from . import config


@dataclass
class TagLocation:
    """A normalised snapshot of one Find My item."""

    device_id: str
    name: str
    latitude: Optional[float]
    longitude: Optional[float]
    accuracy: Optional[float]
    # Epoch milliseconds of the fix, as reported by Find My.
    timestamp: Optional[int]
    battery_status: Optional[int]
    address: Optional[str]

    def has_location(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    def to_dict(self) -> dict:
        return asdict(self)


def _format_address(item: dict) -> Optional[str]:
    address = item.get("address") or {}
    # Find My exposes several address shapes; prefer the most complete.
    for key in ("mapItemFullAddress", "streetAddress", "label"):
        value = address.get(key)
        if value:
            return value
    return None


def _parse_item(item: dict) -> TagLocation:
    location = item.get("location") or {}

    # Find My identifies items by "identifier"; fall back to serial number or
    # name so we always have a stable key.
    device_id = (
        item.get("identifier")
        or item.get("serialNumber")
        or item.get("name")
        or "unknown"
    )

    return TagLocation(
        device_id=str(device_id),
        name=item.get("name") or "(이름 없음)",
        latitude=location.get("latitude"),
        longitude=location.get("longitude"),
        accuracy=location.get("horizontalAccuracy"),
        timestamp=location.get("timeStamp"),
        battery_status=item.get("batteryStatus"),
        address=_format_address(item),
    )


def read_items(path: Optional[Path] = None) -> list[TagLocation]:
    """Return the list of Find My items from the cache.

    Raises FileNotFoundError if the cache is missing (e.g. not running on a
    Mac, or the Find My app has never been opened).
    """
    path = path or config.ITEMS_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"FindMy 캐시 파일을 찾을 수 없습니다: {path}\n"
            "Mac에서 iCloud에 로그인하고 '나의 찾기(Find My)' 앱을 한 번 이상 "
            "실행했는지 확인하세요. 개발 중이라면 APPLETAG_ITEMS_PATH 환경변수로 "
            "샘플 파일을 지정할 수 있습니다."
        )

    with path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)

    if not isinstance(raw, list):
        raise ValueError("예상치 못한 FindMy 캐시 형식입니다 (JSON 배열이 아님).")

    return [_parse_item(item) for item in raw]


def get_item(device_id: str, path: Optional[Path] = None) -> Optional[TagLocation]:
    """Return a single item by id, or None if not present."""
    for item in read_items(path):
        if item.device_id == device_id:
            return item
    return None

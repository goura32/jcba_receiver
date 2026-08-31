"""Optional current-program metadata client."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

TIMETABLE_URL = "https://api.radimo.smen.biz/api/v1/mobile/timetables"


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


async def get_current_program(station_id: str) -> dict[str, str] | None:
    """Return current program when the station exposes a parseable timetable."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(8, connect=5)) as client:
            response = await client.get(TIMETABLE_URL, params={"station": station_id})
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError):
        return None

    if not isinstance(payload, (list, dict)):
        return None
    entries = payload if isinstance(payload, list) else payload.get("timetables", payload.get("data", []))
    if not isinstance(entries, list):
        return None
    return current_from_entries(entries, datetime.now(UTC))


def current_from_entries(entries: list[object], now: datetime) -> dict[str, str] | None:
    """Select a current program while tolerating malformed timetable items."""
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        start, end = _parse_time(entry.get("start")), _parse_time(entry.get("end"))
        if start and end and start <= now < end:
            return {
                "title": entry.get("title") or "番組情報はありません",
                "performer": entry.get("performer") or "",
                "detail": entry.get("detail") or entry.get("sub_title") or "",
            }
    return None

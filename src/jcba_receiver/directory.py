"""Official JCBA station directory fetch, parser, and local cache."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import httpx

from .catalog import STATIONS

DIRECTORY_URL = "https://www.jcbasimul.com/"
CACHE_PATH = Path.home() / ".cache" / "jcba-receiver" / "stations.json"


def _is_station(item: object) -> bool:
    return (
        isinstance(item, dict)
        and all(isinstance(item.get(key), str) and item[key] for key in ("id", "name"))
        and all(isinstance(item.get(key), str) for key in ("region", "prefecture"))
    )


def parse_stations(html: str) -> list[dict[str, str]]:
    """Extract the embedded station array without depending on a script path."""
    marker = '"stations":['
    start = html.find(marker)
    if start == -1:
        return []
    try:
        data, _ = json.JSONDecoder().raw_decode(html[start + len(marker) - 1 :])
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    stations = []
    seen_ids: set[str] = set()
    grouped = [entry.get("list") for entry in data if isinstance(entry, dict) and "list" in entry]
    entries = [item for group in grouped if isinstance(group, list) for item in group] if grouped else data
    for item in entries:
        if not isinstance(item, dict) or not all(isinstance(item.get(key), str) for key in ("id", "name")):
            continue
        station = {
            "id": item["id"],
            "name": item["name"],
            "region": item.get("region") if isinstance(item.get("region"), str) else "",
            "prefecture": item.get("prefecture") if isinstance(item.get("prefecture"), str) else "",
        }
        if not _is_station(station) or station["id"] in seen_ids:
            continue
        seen_ids.add(station["id"])
        stations.append(station)
    return stations


class StationDirectory:
    def __init__(self, cache_path: Path = CACHE_PATH) -> None:
        self.cache_path = cache_path
        self.stations = self._load_cache() or STATIONS

    def find(self, station_id: str) -> dict[str, str] | None:
        return next((station for station in self.stations if station["id"] == station_id), None)

    def _load_cache(self) -> list[dict[str, str]]:
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            if not isinstance(data, list) or not data or not all(_is_station(item) for item in data):
                return []
            station_ids = {item["id"] for item in data}
            return data if len(station_ids) == len(data) else []
        except (OSError, json.JSONDecodeError):
            return []

    async def refresh(self) -> list[dict[str, str]]:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10, connect=5)) as client:
            response = await client.get(DIRECTORY_URL)
            response.raise_for_status()
        stations = parse_stations(response.text)
        if not stations:
            raise ValueError("JCBA directory did not contain station data")
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.cache_path.parent,
            prefix=f".{self.cache_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_file.write(json.dumps(stations, ensure_ascii=False))
            temp_path = Path(temp_file.name)
        temp_path.replace(self.cache_path)
        self.stations = stations
        return stations

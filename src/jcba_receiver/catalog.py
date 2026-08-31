"""Curated station directory keyed by official JCBA station IDs."""

from __future__ import annotations

STATIONS = [
    {"id": "fmnanami", "name": "FMななみ", "prefecture": "北海道", "region": "北海道"},
    {"id": "fmichinomiya", "name": "i-wave", "prefecture": "愛知県", "region": "東海"},
    {"id": "radiosanq", "name": "RADIO SANQ", "prefecture": "愛知県", "region": "東海"},
    {"id": "swave", "name": "S-Wave", "prefecture": "静岡県", "region": "東海"},
    {"id": "fmshingu", "name": "FM新宮", "prefecture": "和歌山県", "region": "近畿"},
    {"id": "fmmahoroba", "name": "FMまほろば", "prefecture": "奈良県", "region": "近畿"},
    {"id": "lovefm", "name": "LCV FM", "prefecture": "長野県", "region": "甲信越"},
    {"id": "fmyaizu", "name": "RADIO LUSH", "prefecture": "静岡県", "region": "東海"},
    {"id": "bingo", "name": "FMふくやま", "prefecture": "広島県", "region": "中国"},
    {"id": "kyotoribingufm", "name": "FM845", "prefecture": "京都府", "region": "近畿"},
    {"id": "rinsaikanto", "name": "関東臨時災害放送局訓練", "prefecture": "関東", "region": "関東"},
]


def find_station(station_id: str) -> dict[str, str] | None:
    return next((station for station in STATIONS if station["id"] == station_id), None)


def filter_stations(region: str, query: str, favorites: set[str]) -> list[dict[str, str]]:
    """Filter client-requested directory data while preserving favorite priority."""
    needle = query.casefold().strip()

    if not region and not needle and not favorites:
        return STATIONS

    def matches(station: dict[str, str]) -> bool:
        haystack = " ".join(station.values()).casefold()
        return (not region or region.casefold() in haystack) and (not needle or needle in haystack)

    return sorted(
        (station for station in STATIONS if matches(station)),
        key=lambda station: (station["id"] not in favorites, station["name"]),
    )

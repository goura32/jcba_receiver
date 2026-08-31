from jcba_receiver.catalog import STATIONS, filter_stations, find_station


def test_catalog_contains_known_station_with_real_station_id():
    station = find_station("fmnanami")

    assert station is not None
    assert station["name"] == "FMななみ"
    assert station["prefecture"] == "北海道"


def test_filter_stations_matches_name_region_and_favorites_first():
    filtered = filter_stations("愛知", "", {"radiosanq"})

    assert filtered[0]["id"] == "radiosanq"
    assert {station["id"] for station in filtered} >= {"radiosanq", "fmichinomiya"}


def test_filter_stations_returns_all_for_empty_query():
    assert filter_stations("", "", set()) == STATIONS

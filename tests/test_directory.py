from jcba_receiver.catalog import STATIONS
from jcba_receiver.directory import StationDirectory, parse_stations


def test_parse_stations_extracts_official_ids_and_display_metadata():
    html = '<script>window.__DATA__={"stations":[{"id":"fmnanami","name":"エフエム ななみ","region":"東海","prefecture":"愛知県","city":"津島市"}]}</script>'

    assert parse_stations(html) == [
        {"id": "fmnanami", "name": "エフエム ななみ", "region": "東海", "prefecture": "愛知県"}
    ]


def test_parse_stations_returns_empty_list_when_embedded_data_is_absent():
    assert parse_stations("<html>no stations</html>") == []


def test_parse_stations_ignores_malformed_group_lists():
    html = '<script>{"stations":[{"list":null},{"list":{"id":"bad"}}]}</script>'

    assert parse_stations(html) == []


def test_parse_stations_rejects_empty_and_duplicate_ids():
    html = '''<script>{"stations":[
        {"id":"","name":"Empty","region":"東海","prefecture":"愛知県"},
        {"id":"valid","name":"Valid","region":"東海","prefecture":"愛知県"},
        {"id":"valid","name":"Duplicate","region":"東海","prefecture":"愛知県"}
    ]}</script>'''

    assert parse_stations(html) == [
        {"id": "valid", "name": "Valid", "region": "東海", "prefecture": "愛知県"}
    ]


def test_directory_ignores_malformed_cache(tmp_path):
    cache = tmp_path / "stations.json"
    cache.write_text('["not-a-station"]', encoding="utf-8")

    assert StationDirectory(cache).stations == STATIONS


def test_directory_ignores_cache_with_duplicate_station_ids(tmp_path):
    cache = tmp_path / "stations.json"
    cache.write_text(
        '[{"id":"duplicate","name":"One","region":"東海","prefecture":"愛知県"},'
        '{"id":"duplicate","name":"Two","region":"東海","prefecture":"愛知県"}]',
        encoding="utf-8",
    )

    assert StationDirectory(cache).stations == STATIONS

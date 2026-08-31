from jcba_receiver.directory import parse_stations


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

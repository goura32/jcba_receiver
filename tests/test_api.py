from fastapi.testclient import TestClient

from jcba_receiver.main import create_app


def test_stations_endpoint_serves_catalog_without_tokens():
    with TestClient(create_app()) as client:
        response = client.get("/api/stations")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 6
    assert any(station["id"] == "fmnanami" for station in payload["stations"])
    assert "token" not in response.text


def test_stream_endpoint_rejects_unknown_station_before_external_call():
    with TestClient(create_app()) as client:
        response = client.get("/api/stream/not-a-station")

    assert response.status_code == 404
    assert response.json()["detail"] == "Station not found"

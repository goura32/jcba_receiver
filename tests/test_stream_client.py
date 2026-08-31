import httpx
import pytest

from jcba_receiver.stream_client import JcbaClient, StreamSessionError, StreamUnavailableError


@pytest.mark.asyncio
async def test_create_session_maps_api_success_to_session():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["station"] == "fmnanami"
        assert request.url.params["channel"] == "0"
        assert request.url.params["quality"] == "high"
        assert request.url.params["burst"] == "5"
        return httpx.Response(
            200,
            json={"code": 200, "token": "secret", "location": "wss://os1305.radimo.smen.biz/socket?burst=5"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = JcbaClient(http_client=http_client)
        session = await client.create_session("fmnanami")

    assert session.location == "wss://os1305.radimo.smen.biz/socket?burst=5"
    assert session.token == "secret"


@pytest.mark.asyncio
async def test_create_session_maps_404_to_unavailable():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(404, json={"code": 404}))
    ) as http_client:
        client = JcbaClient(http_client=http_client)
        with pytest.raises(StreamUnavailableError):
            await client.create_session("rinsaikanto")


@pytest.mark.asyncio
async def test_create_session_rejects_untrusted_websocket_location():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"code": 200, "token": "secret", "location": "wss://attacker.example/socket"},
            )
        )
    ) as http_client:
        client = JcbaClient(http_client=http_client)
        with pytest.raises(StreamSessionError):
            await client.create_session("fmnanami")


@pytest.mark.asyncio
async def test_create_session_rejects_non_object_json():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=["not", "a", "session"]))
    ) as http_client:
        client = JcbaClient(http_client=http_client)
        with pytest.raises(StreamSessionError):
            await client.create_session("fmnanami")


@pytest.mark.asyncio
async def test_create_session_maps_invalid_json_to_session_error():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"{invalid"))
    ) as http_client:
        with pytest.raises(StreamSessionError):
            await JcbaClient(http_client=http_client).create_session("fmnanami")


@pytest.mark.asyncio
async def test_create_session_rejects_invalid_location_port():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={"code": 200, "token": "secret", "location": "wss://os1305.radimo.smen.biz:bad/socket"},
            )
        )
    ) as http_client:
        with pytest.raises(StreamSessionError):
            await JcbaClient(http_client=http_client).create_session("fmnanami")

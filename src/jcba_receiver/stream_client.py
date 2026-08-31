"""JCBA session API and WebSocket relay client."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
import websockets

logger = logging.getLogger(__name__)
SESSION_URL = "https://api.radimo.smen.biz/api/v1/select_stream"
ORIGIN = "https://www.jcbasimul.com"
SUBPROTOCOL = "listener.fmplapla.com"


class JcbaError(Exception):
    """Base error for the remote JCBA service."""


class StreamUnavailableError(JcbaError):
    """The station currently has no obtainable stream session."""


class StreamSessionError(JcbaError):
    """The stream API returned an invalid or unsuccessful response."""


class WebSocketConnectionError(JcbaError):
    """A session could not produce valid Ogg audio."""


@dataclass(frozen=True)
class StreamSession:
    token: str
    location: str


class JcbaClient:
    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        self._http_client = http_client

    async def create_session(self, station_id: str, burst: int = 5) -> StreamSession:
        params = {"station": station_id, "channel": 0, "quality": "high", "burst": burst}
        owns_client = self._http_client is None
        client = self._http_client or httpx.AsyncClient(timeout=httpx.Timeout(10, connect=5))
        try:
            response = await client.get(SESSION_URL, params=params)
            if response.status_code == 404:
                raise StreamUnavailableError("The station is currently unavailable")
            response.raise_for_status()
            try:
                payload = response.json()
            except ValueError as exc:
                raise StreamSessionError("Invalid stream session response") from exc
            if not isinstance(payload, dict):
                raise StreamSessionError("Invalid stream session response")
            token, location = payload.get("token"), payload.get("location")
            if (
                payload.get("code") != 200
                or not isinstance(token, str)
                or not isinstance(location, str)
                or not self._is_trusted_location(location)
            ):
                raise StreamSessionError("Invalid stream session response")
            return StreamSession(token=token, location=location)
        except httpx.HTTPError as exc:
            raise StreamSessionError("Unable to obtain a stream session") from exc
        finally:
            if owns_client:
                await client.aclose()

    @staticmethod
    def _is_trusted_location(location: str) -> bool:
        parsed = urlparse(location)
        try:
            return (
                parsed.scheme == "wss"
                and parsed.hostname is not None
                and parsed.hostname.endswith(".radimo.smen.biz")
                and parsed.path == "/socket"
                and parsed.port in (None, 443)
            )
        except ValueError:
            return False

    async def relay_ogg(
        self, station_id: str, initial_session: StreamSession | None = None
    ) -> AsyncIterator[bytes]:
        """Yield Ogg pages, renewing session after transient WSS disconnects."""
        delays = (1, 2, 5)
        for attempt, delay in enumerate((*delays, None)):
            session = initial_session if attempt == 0 and initial_session else await self.create_session(station_id)
            try:
                async with websockets.connect(
                    session.location,
                    origin=ORIGIN,
                    subprotocols=[SUBPROTOCOL],
                    open_timeout=10,
                    ping_interval=20,
                    ping_timeout=15,
                ) as socket:
                    await socket.send(session.token)
                    while True:
                        message = await asyncio.wait_for(socket.recv(), timeout=15)
                        if not isinstance(message, bytes):
                            continue
                        if not message.startswith(b"OggS"):
                            raise WebSocketConnectionError("Unexpected audio frame")
                        yield message
            except StreamUnavailableError:
                raise
            except (TimeoutError, websockets.WebSocketException, WebSocketConnectionError) as exc:
                if delay is None:
                    raise WebSocketConnectionError("Stream connection could not be restored") from exc
                logger.info("Stream disconnected for %s; reconnecting in %ss", station_id, delay)
                await asyncio.sleep(delay)
                continue
            break

"""ASGI entrypoint for the JCBA receiver."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .audio import transcode_to_mp3
from .directory import StationDirectory
from .programs import get_current_program
from .stream_client import JcbaClient, StreamSessionError, StreamUnavailableError, WebSocketConnectionError

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.jcba_client = JcbaClient()
    app.state.directory = StationDirectory()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="JCBA Receiver", docs_url=None, redoc_url=None, lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/stations")
    async def stations(refresh: bool = False) -> dict[str, object]:
        directory: StationDirectory = app.state.directory
        if refresh:
            try:
                await directory.refresh()
            except (httpx.HTTPError, OSError, ValueError):
                pass
        return {"stations": directory.stations, "count": len(directory.stations)}

    @app.get("/api/programs/{station_id}")
    async def current_program(station_id: str) -> dict[str, object]:
        if app.state.directory.find(station_id) is None:
            raise HTTPException(status_code=404, detail="Station not found")
        return {"program": await get_current_program(station_id)}

    @app.get("/api/stream/{station_id}")
    async def stream(station_id: str) -> StreamingResponse:
        if app.state.directory.find(station_id) is None:
            raise HTTPException(status_code=404, detail="Station not found")
        client: JcbaClient = app.state.jcba_client

        session = None

        async def body():
            try:
                async for chunk in transcode_to_mp3(client.relay_ogg(station_id, session)):
                    yield chunk
            except StreamUnavailableError as exc:
                # Headers may already be committed, so this route preflights below.
                raise exc

        try:
            session = await client.create_session(station_id)
        except StreamUnavailableError as exc:
            raise HTTPException(status_code=503, detail="This station is currently unavailable") from exc
        except StreamSessionError as exc:
            raise HTTPException(status_code=502, detail="Unable to create a stream session") from exc

        return StreamingResponse(
            body(),
            media_type="audio/mpeg",
            headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
        )

    return app


app = create_app()


def run() -> None:
    uvicorn.run("jcba_receiver.main:app", host="127.0.0.1", port=8000, reload=False)

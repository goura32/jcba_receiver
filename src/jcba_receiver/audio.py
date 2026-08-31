"""Streaming audio conversion for browser-compatible live playback."""

from __future__ import annotations

import asyncio
import logging
import shutil
from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


class AudioTranscodeError(Exception):
    """The ffmpeg relay cannot produce browser-compatible audio."""


def ensure_ffmpeg_available() -> None:
    if shutil.which("ffmpeg") is None:
        raise AudioTranscodeError("ffmpeg is not installed or not on PATH")


def mp3_transcoder_command() -> list[str]:
    """Build the low-latency ffmpeg command used for an Ogg/Opus relay."""
    return [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-fflags",
        "+nobuffer",
        "-i",
        "pipe:0",
        "-c:a",
        "libmp3lame",
        "-b:a",
        "96k",
        "-flush_packets",
        "1",
        "-f",
        "mp3",
        "pipe:1",
    ]


async def transcode_to_mp3(ogg_pages: AsyncIterator[bytes]) -> AsyncIterator[bytes]:
    """Convert a continuous Ogg page generator into a browser-friendly MP3 stream."""
    ensure_ffmpeg_available()
    try:
        process = await asyncio.create_subprocess_exec(
            *mp3_transcoder_command(),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
    except OSError as exc:
        raise AudioTranscodeError("Unable to start ffmpeg") from exc
    stdin, stdout = process.stdin, process.stdout
    assert stdin and stdout

    async def write_input() -> None:
        try:
            async for page in ogg_pages:
                stdin.write(page)
                await stdin.drain()
        finally:
            stdin.close()

    writer = asyncio.create_task(write_input())
    try:
        while chunk := await stdout.read(8192):
            yield chunk
    finally:
        if not writer.done():
            writer.cancel()
        writer_result = (await asyncio.gather(writer, return_exceptions=True))[0]
        if process.returncode is None:
            try:
                process.terminate()
            except ProcessLookupError:
                pass
        try:
            await asyncio.wait_for(process.wait(), timeout=3)
        except TimeoutError:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            await process.wait()
        if isinstance(writer_result, Exception):
            logger.warning("Audio relay input failed: %s", writer_result)
        if process.returncode not in (0, -15):
            logger.warning("ffmpeg exited with %s", process.returncode)

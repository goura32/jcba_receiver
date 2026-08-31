"""Streaming audio conversion for browser-compatible live playback."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator


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
    process = await asyncio.create_subprocess_exec(
        *mp3_transcoder_command(),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
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
        await asyncio.gather(writer, return_exceptions=True)
        if process.returncode is None:
            process.terminate()
        await process.wait()

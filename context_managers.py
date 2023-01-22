import asyncio
from contextlib import asynccontextmanager
from enum import Enum
from typing import ContextManager


@asynccontextmanager
async def open_connection(host: str, port: int) -> ContextManager:
    reader, writer = await asyncio.open_connection(host, port)
    try:
        yield reader, writer
    finally:
        writer.close()
        await writer.wait_closed()


@asynccontextmanager
async def open_connection_queue(
        host: str,
        port: int,
        queue: asyncio.Queue,
        init_message: Enum,
        established_message: Enum,
        closed_message: Enum,
) -> ContextManager:
    queue.put_nowait(init_message)
    reader, writer = await asyncio.open_connection(host, port)
    try:
        queue.put_nowait(established_message)
        yield reader, writer
    finally:
        queue.put_nowait(closed_message)
        writer.close()
        await writer.wait_closed()

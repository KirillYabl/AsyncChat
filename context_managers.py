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
async def open_connection_queue(host: str, port: int, queue: asyncio.Queue, message: Enum) -> ContextManager:
    reader, writer = await asyncio.open_connection(host, port)
    try:
        yield reader, writer
    finally:
        queue.put_nowait(message)
        writer.close()
        await writer.wait_closed()

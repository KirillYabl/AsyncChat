import asyncio
from contextlib import asynccontextmanager
from typing import ContextManager


@asynccontextmanager
async def open_connection(host: str, port: int) -> ContextManager:
    reader, writer = await asyncio.open_connection(host, port)
    try:
        yield reader, writer
    finally:
        writer.close()
        await writer.wait_closed()

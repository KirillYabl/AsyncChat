import asyncio
import argparse
from dataclasses import dataclass
import logging

import gui
from context_managers import open_connection

logger = logging.getLogger(__name__)


async def read_msgs(host, port, queue: asyncio.Queue) -> None:
    async with open_connection(host, port) as (reader, writer):
        while not reader.at_eof():
            message = await reader.readline()
            message = message.decode().strip()
            logger.debug(f'RECEIVE: {message}')
            queue.put_nowait(message)


@dataclass
class Options:
    listen_host: str
    listen_port: int


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    parser = argparse.ArgumentParser(
        prog='Async chat listener',
        description='Script for chat listening and write in file',
    )

    parser.add_argument('-lh', '--listen_host', type=str, required=True, help='host of chat to listen')
    parser.add_argument('-lp', '--listen_port', type=int, required=True, help='port of chat to listen')

    args = parser.parse_args()

    options = Options(**args.__dict__)

    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()

    loop.run_until_complete(asyncio.gather(
        read_msgs(options.listen_host, options.listen_port, messages_queue),
        gui.draw(messages_queue, sending_queue, status_updates_queue)
    ))

import asyncio
import argparse
import datetime
from dataclasses import dataclass
import logging
from pathlib import Path

import aiofiles

import gui
from context_managers import open_connection

logger = logging.getLogger(__name__)


async def read_msgs(host: str, port: int, filepath: Path,
                    messages_queue: asyncio.Queue, messages_to_file_queue: asyncio.Queue) -> None:

    # read history of chat
    async with aiofiles.open(filepath, 'r', encoding='UTF8') as f:
        async for message in f:
            messages_queue.put_nowait(message.strip())

    # read live messages
    async with open_connection(host, port) as (reader, writer):
        while not reader.at_eof():
            message = await reader.readline()
            message = message.decode().strip()
            logger.debug(f'RECEIVE: {message}')
            messages_queue.put_nowait(message)
            messages_to_file_queue.put_nowait(message)


async def save_msgs(filepath: Path, queue: asyncio.Queue) -> None:
    async with aiofiles.open(filepath, 'a', encoding='UTF8') as f:
        while True:
            message = await queue.get()
            formatted_now = datetime.datetime.now().strftime('%d.%m.%y %H:%M')
            message = f'[{formatted_now}] {message}\n'
            await f.write(message)


@dataclass
class Options:
    listen_host: str
    listen_port: int
    history_path: Path


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    parser = argparse.ArgumentParser(
        prog='Async chat listener',
        description='Script for chat listening and write in file',
    )

    parser.add_argument('-lh', '--listen_host', type=str, required=True, help='host of chat to listen')
    parser.add_argument('-lp', '--listen_port', type=int, required=True, help='port of chat to listen')
    parser.add_argument('-hp', '--history_path',
                        type=Path, default='chat_history.txt', help='path to file with messages')

    args = parser.parse_args()

    options = Options(**args.__dict__)

    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    messages_to_file_queue = asyncio.Queue()

    loop.run_until_complete(asyncio.gather(
        read_msgs(options.listen_host, options.listen_port, options.history_path, messages_queue, messages_to_file_queue),
        save_msgs(options.history_path, messages_to_file_queue),
        gui.draw(messages_queue, sending_queue, status_updates_queue)
    ))

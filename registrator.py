import asyncio
import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from tkinter import TclError
import logging

import aiofiles
import anyio

import registrator_gui as gui
from context_managers import open_connection

logger = logging.getLogger(__name__)


async def write_message(writer: asyncio.StreamWriter, text: str) -> None:
    """Wrapper of stream message sending"""
    text = text.encode()
    logger.debug(f'SEND: {text}')
    writer.write(text)
    await writer.drain()


async def register(host: str, port: int, credential_path: Path, sending_queue: asyncio.Queue,
                   creds_updates_queue: asyncio.Queue) -> None:
    """Register in chat coroutine. While true loop because interface supports many registrations"""
    while True:
        logger.info('registration...')
        async with open_connection(host, port) as (reader, writer):
            greeting_msg = await reader.readline()
            logger.debug(f'RECEIVE: {greeting_msg.decode().strip()}')

            # send null for registration
            await write_message(writer, '\n')

            instruction_msg = await reader.readline()
            logger.debug(f'RECEIVE: {instruction_msg.decode().strip()}')

            username = await sending_queue.get()

            await write_message(writer, f'{username}\n')

            credentials_msg = await reader.readline()
            logger.debug(f'RECEIVE: {credentials_msg.decode().strip()}')

        credentials = json.loads(credentials_msg.decode().strip())

        creds_updates_queue.put_nowait(
            gui.Credentials(nickname=credentials['nickname'], token=credentials['account_hash']))

        async with aiofiles.open(credential_path, 'a', encoding='UTF8') as f:
            await f.write(json.dumps(credentials) + '\n')

        logger.info('success registration')


@dataclass
class Options:
    listen_host: str
    listen_port: int
    history_path: Path
    write_host: str
    write_port: int
    credential_path: Path
    token: str = ''


async def main():
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(
        prog='Registration in chat UI',
        description='UI for registration users in chat with possibility going to chat',
    )

    parser.add_argument('-lh', '--listen_host', type=str, required=True, help='host of chat to listen')
    parser.add_argument('-lp', '--listen_port', type=int, required=True, help='port of chat to listen')
    parser.add_argument('-hp', '--history_path',
                        type=Path, default='chat_history.txt', help='path to file with messages')
    parser.add_argument('-wh', '--write_host', type=str, required=True, help='host of chat to write')
    parser.add_argument('-wp', '--write_port', type=int, required=True, help='port of chat to write')
    parser.add_argument('-cp', '--credential_path',
                        type=Path, default='creds.jsonstream', help='path to file with credentials')

    args = parser.parse_args()

    options = Options(**args.__dict__)

    sending_queue = asyncio.Queue()
    creds_updates_queue = asyncio.Queue()
    async with anyio.create_task_group() as tg:
        tg.start_soon(gui.draw, sending_queue, creds_updates_queue, options)
        tg.start_soon(register, options.write_host, options.write_port, options.credential_path,
                      sending_queue, creds_updates_queue)


if __name__ == '__main__':
    try:
        anyio.run(main)
    except (KeyboardInterrupt, gui.TkAppClosed, TclError):
        pass

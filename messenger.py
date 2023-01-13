import asyncio
import argparse
import datetime
import json
from dataclasses import dataclass
import logging
from pathlib import Path
from tkinter import messagebox
from typing import Any

import aiofiles

import gui
from context_managers import open_connection, open_connection_queue

logger = logging.getLogger(__name__)


async def read_msgs(host: str, port: int, filepath: Path,
                    messages_queue: asyncio.Queue, messages_to_file_queue: asyncio.Queue,
                    status_updates_queue: asyncio.Queue) -> None:
    # read history of chat
    async with aiofiles.open(filepath, 'r', encoding='UTF8') as f:
        async for message in f:
            messages_queue.put_nowait(message.strip())

    status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.INITIATED)
    # read live messages
    async with open_connection_queue(host, port, status_updates_queue,
                                     gui.ReadConnectionStateChanged.CLOSED) as (reader, writer):
        status_updates_queue.put_nowait(gui.ReadConnectionStateChanged.ESTABLISHED)
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


async def send_msgs(host: str, port: int, token: str, queue: asyncio.Queue,
                    status_updates_queue: asyncio.Queue) -> None:
    while True:
        message = await queue.get()
        await submit_message(host, port, token, message, status_updates_queue)


async def write_message_in_stream(writer: asyncio.StreamWriter, text: str) -> None:
    text = text.encode()
    logger.debug(f'SEND: {text}')
    writer.write(text)
    await writer.drain()


async def authorize_in_chat_by_token(host: str, port: int, token: str) -> tuple[bool, dict[str, Any]]:
    """
    Authorization by token from args
    Return bool value of authorization result
    """
    logger.info(f'authorization...')
    async with open_connection(host, port) as (reader, writer):
        greeting_msg = await reader.readline()
        logger.debug(f'RECEIVE: {greeting_msg.decode().strip()}')

        await write_message_in_stream(writer, f'{token}\n')

        credentials_msg = await reader.readline()
        logger.debug(f'RECEIVE: {credentials_msg.decode().strip()}')

        creds = json.loads(credentials_msg.decode().strip())

        if not creds:
            logger.error(f'Wrong token {token}')
            return False, {}

    logger.info(f'success authorization')
    return True, creds


async def submit_message(host: str, port: int, token: str, message: str,
                         status_updates_queue: asyncio.Queue) -> None:
    """
    Submit message in chat.
    In this function token always in options and always valid
    """
    logger.info(f'submit message...')
    status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.INITIATED)
    async with open_connection_queue(host, port, status_updates_queue,
                                     gui.SendingConnectionStateChanged.CLOSED) as (reader, writer):
        status_updates_queue.put_nowait(gui.SendingConnectionStateChanged.ESTABLISHED)
        greeting_msg = await reader.readline()
        logger.debug(f'RECEIVE: {greeting_msg.decode().strip()}')

        await write_message_in_stream(writer, f'{token}\n')

        authorization_msg = await reader.readline()
        logger.debug(f'RECEIVE: {authorization_msg.decode().strip()}')

        # double \n because chat require empty string for message sending
        await write_message_in_stream(writer, f'{message}\n\n')

        logger.info(f'message submitted')


@dataclass
class Options:
    listen_host: str
    listen_port: int
    history_path: Path
    write_host: str
    write_port: int
    token: str


async def main():
    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser(
        prog='Async chat listener',
        description='Script for chat listening and write in file',
    )

    parser.add_argument('-lh', '--listen_host', type=str, required=True, help='host of chat to listen')
    parser.add_argument('-lp', '--listen_port', type=int, required=True, help='port of chat to listen')
    parser.add_argument('-hp', '--history_path',
                        type=Path, default='chat_history.txt', help='path to file with messages')
    parser.add_argument('-wh', '--write_host', type=str, required=True, help='host of chat to write')
    parser.add_argument('-wp', '--write_port', type=int, required=True, help='port of chat to write')
    parser.add_argument('-t', '--token', type=str, required=True, help='token of registered user')

    args = parser.parse_args()

    options = Options(**args.__dict__)

    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()
    messages_to_file_queue = asyncio.Queue()

    is_authorize, creds = await authorize_in_chat_by_token(options.write_host, options.write_port, options.token)
    if not is_authorize:
        messagebox.showinfo("Неверный токен", "Проверьте токен, сервер его не узнал")
    else:
        status_updates_queue.put_nowait(gui.NicknameReceived(creds['nickname']))
        await asyncio.gather(
            read_msgs(options.listen_host, options.listen_port, options.history_path, messages_queue,
                      messages_to_file_queue, status_updates_queue),
            save_msgs(options.history_path, messages_to_file_queue),
            send_msgs(options.write_host, options.write_port, options.token, sending_queue, status_updates_queue),
            gui.draw(messages_queue, sending_queue, status_updates_queue)
        )


if __name__ == '__main__':
    asyncio.run(main())

import asyncio
from asyncio.exceptions import TimeoutError
import argparse
import datetime
import json
from dataclasses import dataclass
import logging
from pathlib import Path
from tkinter import messagebox, TclError
from typing import Any

import anyio
import aiofiles
from async_timeout import timeout

import messenger_gui as gui
from context_managers import open_connection, open_connection_queue


class Messenger:
    def __init__(self, *, messages_queue: asyncio.Queue, sending_queue: asyncio.Queue,
                 status_updates_queue: asyncio.Queue, listen_host: str, listen_port: int,
                 history_path: Path, write_host: str, write_port: int, token: str):
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.history_path = history_path
        self.write_host = write_host
        self.write_port = write_port
        self.token = token
        self.logger = logging.getLogger('messenger')
        self.watchdog_logger = logging.getLogger('watchdog')
        ch = logging.StreamHandler()
        formatter = logging.Formatter('[%(created)i] %(message)s')
        ch.setFormatter(formatter)
        self.watchdog_logger.addHandler(ch)

        self.messages_queue = messages_queue
        self.sending_queue = sending_queue
        self.status_updates_queue = status_updates_queue
        self.messages_to_file_queue = asyncio.Queue()
        self.watchdog_queue = asyncio.Queue()

        self._read_history_messages()

    def _read_history_messages(self) -> None:
        """Call only once on init to read all saved messages"""
        with open(self.history_path, 'r', encoding='UTF8') as f:
            for message in f:
                self.messages_queue.put_nowait(message.strip())

    async def read_msgs(self) -> None:
        async with open_connection_queue(
                self.listen_host,
                self.listen_port,
                self.status_updates_queue,
                gui.ReadConnectionStateChanged.INITIATED,
                gui.ReadConnectionStateChanged.ESTABLISHED,
                gui.ReadConnectionStateChanged.CLOSED
        ) as (reader, writer):
            self.watchdog_queue.put_nowait('Connection established')
            while not reader.at_eof():
                message = await reader.readline()
                message = message.decode().strip()
                self.logger.debug(f'RECEIVE: {message}')
                self.messages_queue.put_nowait(message)
                self.messages_to_file_queue.put_nowait(message)
                self.watchdog_queue.put_nowait('New message in chat')

    async def save_msgs(self) -> None:
        async with aiofiles.open(self.history_path, 'a', encoding='UTF8') as f:
            while True:
                message = await self.messages_to_file_queue.get()
                formatted_now = datetime.datetime.now().strftime('%d.%m.%y %H:%M')
                message = f'[{formatted_now}] {message}\n'
                await f.write(message)

    async def send_msgs(self) -> None:
        async with open_connection_queue(
                self.write_host,
                self.write_port,
                self.status_updates_queue,
                gui.SendingConnectionStateChanged.INITIATED,
                gui.SendingConnectionStateChanged.ESTABLISHED,
                gui.SendingConnectionStateChanged.CLOSED,
        ) as (reader, writer):
            await self.get_creds_after_authorization(reader, writer)

            while True:
                message = await self.sending_queue.get()
                # double \n because chat require empty string for message sending
                await self.write_message_in_stream(writer, f'{message}\n\n')

                self.logger.info('message submitted')
                self.watchdog_queue.put_nowait('Message sent')

    async def write_message_in_stream(self, writer: asyncio.StreamWriter, text: str) -> None:
        """Wrapper of stream message sending"""
        text = text.encode()
        self.logger.debug(f'SEND: {text}')
        writer.write(text)
        await writer.drain()

    async def get_creds_after_authorization(
            self,
            reader: asyncio.StreamReader,
            writer: asyncio.StreamWriter
    ) -> dict[str, Any]:
        greeting_msg = await reader.readline()
        self.logger.debug(f'RECEIVE: {greeting_msg.decode().strip()}')

        await self.write_message_in_stream(writer, f'{self.token}\n')

        credentials_msg = await reader.readline()
        self.logger.debug(f'RECEIVE: {credentials_msg.decode().strip()}')

        creds = json.loads(credentials_msg.decode().strip())

        return creds

    async def check_token_for_authorization(self) -> bool:
        """
        Check in authorization if token right

        Return bool value of authorization result
        """
        self.logger.info('authorization...')
        async with open_connection(self.write_host, self.write_port) as (reader, writer):
            creds = await self.get_creds_after_authorization(reader, writer)

            if not creds:
                self.logger.error(f'Wrong token {self.token}')
                messagebox.showinfo("???????????????? ??????????", "?????????????????? ??????????, ???????????? ?????? ???? ??????????")
                return False

        self.status_updates_queue.put_nowait(gui.NicknameReceived(creds['nickname']))
        self.logger.info('success authorization')
        return True

    async def watch_for_connection(self) -> None:
        timeout_seconds = 10
        while True:
            try:
                send_empty_message_every_seconds = 5
                async with timeout(timeout_seconds):
                    message = await self.watchdog_queue.get()
                    self.watchdog_logger.debug(f'Connection is alive. {message}')
                    self.sending_queue.put_nowait('')  # ping pong
                    await anyio.sleep(send_empty_message_every_seconds)
            except TimeoutError:
                self.watchdog_logger.warning(f'{timeout_seconds}s timeout is elapsed')
                raise ConnectionError

    async def handle_connection(self) -> None:
        """Function run all coruutines and try to reconnect if connection lost"""
        try_reconnect_every_seconds = 1
        while True:
            try:
                async with anyio.create_task_group() as tg:
                    tg.start_soon(self.check_token_for_authorization)
                    tg.start_soon(self.read_msgs)
                    tg.start_soon(self.save_msgs)
                    tg.start_soon(self.send_msgs)
                    tg.start_soon(self.watch_for_connection)
            except BaseException:
                self.watchdog_logger.warning('Connection error happened')
                await anyio.sleep(try_reconnect_every_seconds)


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
        prog='Async chat UI',
        description='Asynchronous UI of chat',
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

    messenger = Messenger(
        messages_queue=messages_queue, sending_queue=sending_queue,
        status_updates_queue=status_updates_queue, **options.__dict__
    )
    async with anyio.create_task_group() as tg:
        tg.start_soon(gui.draw, messages_queue, sending_queue, status_updates_queue)
        tg.start_soon(messenger.handle_connection)


if __name__ == '__main__':
    try:
        anyio.run(main)
    except (KeyboardInterrupt, gui.TkAppClosed, TclError):
        pass

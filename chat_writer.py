import argparse
import asyncio
import os.path
from dataclasses import dataclass
import json
import logging
from pathlib import Path

import aiofiles

logger = logging.getLogger(__name__)


@dataclass
class Options:
    host: str
    port: int
    message: str
    token: str
    username: str
    credential_path: Path


def make_msg(text: str, is_end: bool = False) -> bytes:
    """Make suitable for sending message: add newlines and convert to bytes"""
    logger.debug(f'SEND: {text}')
    text = f'{text}\n'
    if is_end:
        # double \n, first for end line and second empty line for end message
        text += '\n'
    return text.encode()


async def registration_in_chat(options: Options) -> dict[str, str]:
    reader, writer = await asyncio.open_connection(options.host, options.port)

    data = await reader.readline()
    logger.debug(f'RECEIVE: {data.decode().strip()}')

    writer.write(make_msg('', is_end=True))
    await writer.drain()

    data = await reader.readline()
    logger.debug(f'RECEIVE: {data.decode().strip()}')

    writer.write(make_msg(options.username))
    await writer.drain()

    data = await reader.readline()
    logger.debug(f'RECEIVE: {data.decode().strip()}')

    credentials = json.loads(data.decode().strip())

    writer.close()
    return credentials


async def write_to_chat(options: Options) -> None:
    reader, writer = await asyncio.open_connection(options.host, options.port)

    data = await reader.readline()
    logger.debug(f'RECEIVE: {data.decode().strip()}')

    writer.write(make_msg(options.token))
    await writer.drain()

    data = await reader.readline()
    logger.debug(f'RECEIVE: {data.decode().strip()}')

    if json.loads(data.decode().strip()) is None:
        logger.error(f'Wrong token {options.token}')
        writer.close()
        return

    data = await reader.readline()
    logger.debug(f'RECEIVE: {data.decode().strip()}')

    writer.write(make_msg(options.message, True))
    await writer.drain()

    writer.close()


async def writer_logic(options: Options) -> None:
    if options.username:
        creds_found = False
        options.credential_path.touch()
        async with aiofiles.open(options.credential_path, encoding='UTF8') as f:
            async for line in f:
                creds = json.loads(line)

                if creds['nickname'] == options.username:
                    creds_found = True
                    credentials = creds
                    break

        if not creds_found:
            credentials = await registration_in_chat(options)
            async with aiofiles.open(options.credential_path, 'a', encoding='UTF8') as f:
                await f.write(json.dumps(credentials) + '\n')
        options.token = credentials['account_hash']

    await write_to_chat(options)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser(
        prog='Async chat writer',
        description='Script for write to chat message',
    )

    parser.add_argument('-host', '--host', type=str, required=True, help='host of chat')
    parser.add_argument('-p', '--port', type=int, required=True, help='port of chat')
    parser.add_argument('-m', '--message', type=str, required=True, help='message to send')
    parser.add_argument('-t', '--token', type=str, default='', help='token of registered user')
    parser.add_argument('-u', '--username', type=str, default='', help='username for new user or cached')
    parser.add_argument('-cp', '--credential_path', type=Path,
                        default=Path('creds.jsonstream'), help='path with credentials')

    args = parser.parse_args()

    options = Options(**args.__dict__)

    asyncio.run(writer_logic(options))

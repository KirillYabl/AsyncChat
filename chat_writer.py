import argparse
import asyncio
from dataclasses import dataclass
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class Options:
    host: str
    port: int
    message: str
    token: str


def make_msg(text: str, is_end: bool = False) -> bytes:
    """Make suitable for sending message: add newlines and convert to bytes"""
    logger.debug(f'SEND: {text}')
    text = f'{text}\n'
    if is_end:
        # double \n, first for end line and second empty line for end message
        text += '\n'
    return text.encode()


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

    args = parser.parse_args()

    options = Options(**args.__dict__)

    asyncio.run(write_to_chat(options))

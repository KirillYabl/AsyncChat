import argparse
import asyncio
from dataclasses import dataclass


@dataclass
class Options:
    host: str
    port: int
    message: str
    token: str = '4632b104-88ff-11ed-8c47-0242ac110002'


def make_msg(text: str, is_end: bool = False) -> bytes:
    """Make suitable for sending message: add newlines and convert to bytes"""
    text = f'{text}\n'
    if is_end:
        # double \n, first for end line and second empty line for end message
        text += '\n'
    return text.encode()


async def write_to_chat(options: Options) -> None:
    reader, writer = await asyncio.open_connection(options.host, options.port)

    writer.write(make_msg(options.token))
    await writer.drain()

    writer.write(make_msg(options.message, True))
    await writer.drain()

    writer.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='Async chat writer',
        description='Script for write to chat message',
    )

    parser.add_argument('-host', '--host', type=str, required=True, help='host of chat')
    parser.add_argument('-p', '--port', type=int, required=True, help='port of chat')
    parser.add_argument('-m', '--message', type=str, required=True, help='message to send')

    args = parser.parse_args()

    options = Options(**args.__dict__)

    asyncio.run(write_to_chat(options))
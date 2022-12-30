import argparse
import asyncio
from dataclasses import dataclass
import datetime
from pathlib import Path

import aiofiles


@dataclass
class Options:
    host: str
    port: int
    history_path: Path


async def tcp_echo_client(options: Options) -> None:
    reader, writer = await asyncio.open_connection(options.host, options.port)

    async with aiofiles.open(options.history_path, 'a', encoding='UTF8') as f:
        while not reader.at_eof():
            data = await reader.readline()
            formatted_now = datetime.datetime.now().strftime('%d.%m.%y %H:%M')
            message = f'[{formatted_now}] {data.decode()}'
            print(message, end='')
            await f.write(message)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='Async chat listener',
        description='Script for chat listening and write in file',
    )

    parser.add_argument('-host', type=str, required=True, help='host of chat')
    parser.add_argument('-p', '--port', type=int, required=True, help='port of chat')
    parser.add_argument('-hp', '--history_path',
                        type=Path, required=True, help='path to file with messages')

    args = parser.parse_args()

    options = Options(**args.__dict__)

    asyncio.run(tcp_echo_client(options))

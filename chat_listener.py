import argparse
import asyncio
from dataclasses import dataclass
import datetime
import logging
from pathlib import Path

import aiofiles

logger = logging.getLogger(__name__)


@dataclass
class Options:
    host: str
    port: int
    history_path: Path
    logging: bool


async def echo_chat(options: Options) -> None:
    reader, writer = await asyncio.open_connection(options.host, options.port)

    async with aiofiles.open(options.history_path, 'a', encoding='UTF8') as f:
        while not reader.at_eof():
            data = await reader.readline()
            formatted_now = datetime.datetime.now().strftime('%d.%m.%y %H:%M')
            message = f'[{formatted_now}] {data.decode()}'
            logger.debug(f'RECEIVE: {message.strip()}')
            await f.write(message)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser(
        prog='Async chat listener',
        description='Script for chat listening and write in file',
    )

    parser.add_argument('-host', '--host', type=str, required=True, help='host of chat')
    parser.add_argument('-p', '--port', type=int, required=True, help='port of chat')
    parser.add_argument('-hp', '--history_path',
                        type=Path, required=True, help='path to file with messages')
    parser.add_argument('-l', '--logging', action='store_true', default=False, help='is do logging')

    args = parser.parse_args()

    options = Options(**args.__dict__)

    if not options.logging:
        logging.disable()

    asyncio.run(echo_chat(options))

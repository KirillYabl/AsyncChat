import argparse
import asyncio
from dataclasses import dataclass
import json
import logging
from pathlib import Path
import platform

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
    logging: bool


async def register(options: Options) -> dict[str, str]:
    logger.info(f'registration...')
    reader, writer = await asyncio.open_connection(options.host, options.port)

    # get greetings message
    data = await reader.readline()
    logger.debug(f'RECEIVE: {data.decode().strip()}')

    # send null for registration
    text = '\n'.encode()
    logger.debug(f'SEND: {text}')
    writer.write(text)
    await writer.drain()

    # get instruction message
    data = await reader.readline()
    logger.debug(f'RECEIVE: {data.decode().strip()}')

    text = f'{options.username}\n'.encode()
    logger.debug(f'SEND: {text}')
    writer.write(text)
    await writer.drain()

    # get message with credentials
    data = await reader.readline()
    logger.debug(f'RECEIVE: {data.decode().strip()}')

    credentials = json.loads(data.decode().strip())

    writer.close()

    async with aiofiles.open(options.credential_path, 'a', encoding='UTF8') as f:
        await f.write(json.dumps(credentials) + '\n')

    logger.info(f'success registration')
    return credentials


async def submit_message(options: Options) -> None:
    """
    Submit message in chat.
    In this function token always in options and always valid
    """
    logger.info(f'submit message...')
    reader, writer = await asyncio.open_connection(options.host, options.port)

    # get greetings message
    data = await reader.readline()
    logger.debug(f'RECEIVE: {data.decode().strip()}')

    text = f'{options.token}\n'.encode()
    logger.debug(f'SEND: {text}')
    writer.write(text)
    await writer.drain()

    # get message with success authorization info
    data = await reader.readline()
    logger.debug(f'RECEIVE: {data.decode().strip()}')

    # double \n because chat require empty string for message sending
    text = f'{options.message}\n\n'.encode()
    logger.debug(f'SEND: {text}')
    writer.write(text)
    await writer.drain()

    writer.close()
    logger.info(f'message submitted')


async def authorize(options: Options) -> bool:
    """
    Authorization from db data by mane or by token from args
    Return bool value of authorization result
    """
    logger.info(f'authorization...')
    reader, writer = await asyncio.open_connection(options.host, options.port)

    # get greetings message
    data = await reader.readline()
    logger.debug(f'RECEIVE: {data.decode().strip()}')

    # token more prior than username
    if options.username and not options.token:
        creds_found = False
        options.credential_path.touch()
        async with aiofiles.open(options.credential_path, encoding='UTF8') as f:
            async for line in f:
                creds = json.loads(line)

                if creds['nickname'] == options.username:
                    creds_found = True
                    options.token = creds['account_hash']
                    break
        if not creds_found:
            return False

    text = f'{options.token}\n'.encode()
    logger.debug(f'SEND: {text}')
    writer.write(text)
    await writer.drain()

    # get message with credentials
    data = await reader.readline()
    logger.debug(f'RECEIVE: {data.decode().strip()}')

    if json.loads(data.decode().strip()) is None:
        logger.error(f'Wrong token {options.token}')
        writer.close()
        return False

    logger.info(f'success authorization')
    return True


async def main(options: Options) -> None:
    is_authorized = await authorize(options)
    if not is_authorized and not options.token:
        credentials = await register(options)
        options.token = credentials['account_hash']
    elif not is_authorized:
        return

    # now we have token from args if success authorization or from registration
    await submit_message(options)


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
    parser.add_argument('-l', '--logging', action='store_true', default=False, help='is do logging')

    args = parser.parse_args()

    options = Options(**args.__dict__)

    if not options.logging:
        logging.disable()

    if platform.system() == 'Windows':
        # without this it will always RuntimeError in the end of function
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main(options))

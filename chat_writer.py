import argparse
import asyncio
from dataclasses import dataclass
import json
import logging
from pathlib import Path
import platform

import aiofiles

from context_managers import open_connection

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


async def write_message(writer: asyncio.StreamWriter, text: str) -> None:
    text = text.encode()
    logger.debug(f'SEND: {text}')
    writer.write(text)
    await writer.drain()


async def register(options: Options) -> dict[str, str]:
    logger.info(f'registration...')
    async with open_connection(options.host, options.port) as (reader, writer):
        greeting_msg = await reader.readline()
        logger.debug(f'RECEIVE: {greeting_msg.decode().strip()}')

        # send null for registration
        await write_message(writer, '\n')

        instruction_msg = await reader.readline()
        logger.debug(f'RECEIVE: {instruction_msg.decode().strip()}')

        await write_message(writer, f'{options.username}\n')

        credentials_msg = await reader.readline()
        logger.debug(f'RECEIVE: {credentials_msg.decode().strip()}')

        credentials = json.loads(credentials_msg.decode().strip())

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
    async with open_connection(options.host, options.port) as (reader, writer):
        greeting_msg = await reader.readline()
        logger.debug(f'RECEIVE: {greeting_msg.decode().strip()}')

        await write_message(writer, f'{options.token}\n')

        authorization_msg = await reader.readline()
        logger.debug(f'RECEIVE: {authorization_msg.decode().strip()}')

        # double \n because chat require empty string for message sending
        await write_message(writer, f'{options.message}\n\n')

        logger.info(f'message submitted')


async def authorize(options: Options) -> bool:
    """
    Authorization from db data by mane or by token from args
    Return bool value of authorization result
    """
    logger.info(f'authorization...')
    async with open_connection(options.host, options.port) as (reader, writer):

        greeting_msg = await reader.readline()
        logger.debug(f'RECEIVE: {greeting_msg.decode().strip()}')

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

        await write_message(writer, f'{options.token}\n')

        credentials_msg = await reader.readline()
        logger.debug(f'RECEIVE: {credentials_msg.decode().strip()}')

        if json.loads(credentials_msg.decode().strip()) is None:
            logger.error(f'Wrong token {options.token}')
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

import asyncio
import datetime

import aiofiles


async def tcp_echo_client(host, port):
    reader, writer = await asyncio.open_connection(host, port)

    async with aiofiles.open('chat_history.txt', 'a', encoding='UTF8') as f:
        while not reader.at_eof():
            data = await reader.readline()
            formatted_now = datetime.datetime.now().strftime('%d.%m.%y %H:%M')
            message = f'[{formatted_now}] {data.decode()}'
            print(message, end='')
            await f.write(message)

if __name__ == '__main__':
    host = 'minechat.dvmn.org'
    port = 5000
    asyncio.run(tcp_echo_client(host, port))

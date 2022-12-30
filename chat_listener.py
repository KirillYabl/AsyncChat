import asyncio


async def tcp_echo_client(host, port):
    reader, writer = await asyncio.open_connection(host, port)

    while not reader.at_eof():
        data = await reader.readline()
        print(data.decode(), end='')


if __name__ == '__main__':
    host = 'minechat.dvmn.org'
    port = 5000
    asyncio.run(tcp_echo_client(host, port))

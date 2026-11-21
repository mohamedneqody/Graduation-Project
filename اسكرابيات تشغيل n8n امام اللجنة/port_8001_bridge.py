import asyncio
import sys

async def pipe(reader, writer):
    try:
        while not reader.at_eof():
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except Exception:
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass

async def handle_client(client_reader, client_writer):
    try:
        server_reader, server_writer = await asyncio.open_connection('127.0.0.1', 8000)
        await asyncio.gather(
            pipe(client_reader, server_writer),
            pipe(server_reader, client_writer)
        )
    except Exception:
        try:
            client_writer.close()
            await client_writer.wait_closed()
        except Exception:
            pass

async def main():
    server = await asyncio.start_server(handle_client, '0.0.0.0', 8001)
    print("Port bridge 8001 -> 8000 is listening on 0.0.0.0:8001")
    sys.stdout.flush()
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())

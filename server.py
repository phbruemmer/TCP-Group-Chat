import asyncio
import socket


HOST = socket.gethostbyname(socket.gethostname())
PORT = 8888
BUFFER = 1024


"""
GENERAL PURPOSE MESSAGES
"""
joining_msg = b"[Lobby] You joined the main lobby!\n[Lobby] Use !help to see a list of commands."
exit_msg = b"[Lobby] Closing connection..."


async def handle_client(client, addr):
    loop = asyncio.get_event_loop()

    await loop.sock_sendto(client, joining_msg, addr)
    data = None
    while not data == "!exit":
        data = ""
        while True:
            recv_data = (await loop.sock_recv(client, BUFFER)).decode()
            data += recv_data
            if len(recv_data) < BUFFER:
                break
        print(data)
        await loop.sock_sendto(client, data.encode(), addr)
    client.close()


async def run_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(8)
    server.setblocking(False)

    loop = asyncio.get_event_loop()

    while True:
        client, addr = await loop.sock_accept(server)
        print(f"[run_server] {addr[0]} connected to this server.")
        await loop.create_task(handle_client(client, addr))


if __name__ == "__main__":
    asyncio.run(run_server())

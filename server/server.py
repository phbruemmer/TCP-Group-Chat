import asyncio
import socket


HOST = socket.gethostbyname(socket.gethostname())
PORT = 8888
BUFFER = 1024

connected_clients = []


"""
GENERAL PURPOSE MESSAGES
"""
joining_msg = b"[Lobby] You joined the main lobby!\n[Lobby] Use !help to see a list of commands."
exit_msg = b"[Lobby] Closing connection..."

help_msg = ("[help] List of commands to use in this lobby.\n!help\t\t\t\t:\tlists all available commands."
            "\n!join [lobby name]\t:\tconnects you to another lobby."
            "\n!lobbies\t\t\t:\tlists all available lobbies.")


def join_lobby(lobby_name):
    return ""


def handle_lobby_commands(cmd):
    cmd = cmd.split(' ')
    print(cmd)
    response = ""

    match cmd[0]:
        case "!help":
            response = help_msg
        case "!join":
            response = join_lobby(cmd[1])
        case _:
            pass
            # ignore

    return response


async def send_all(loop, client_data, data):
    """
    Sends data to all users in that lobby
    :param loop: current event loop
    :param client_data: tuple containing client socket and address
    :param data: data to send to other clients
    :return: None
    """
    client, addr = client_data

    for con_client in connected_clients:
        if not con_client == (client, addr):
            await loop.sock_sendto(con_client[0], data.encode(), con_client[1])


async def handle_client(client, addr):
    loop = asyncio.get_event_loop()

    await loop.sock_sendto(client, joining_msg, addr)
    data = None
    while not data == "!exit":
        data = b""
        while True:
            recv_data = (await loop.sock_recv(client, BUFFER))
            data += recv_data
            if len(recv_data) < BUFFER:
                break
        response = handle_lobby_commands(data.decode())
        await loop.sock_sendto(client, response.encode(), addr)
    client.close()
    connected_clients.remove((client, addr))


async def run_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(8)
    server.setblocking(False)

    loop = asyncio.get_event_loop()

    while True:
        client, addr = await loop.sock_accept(server)
        print(f"[run_server] {addr[0]} connected to this server.")
        connected_clients.append((client, addr))
        loop.create_task(handle_client(client, addr))


if __name__ == "__main__":
    asyncio.run(run_server())

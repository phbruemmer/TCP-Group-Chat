import threading
import asyncio
import json
import socket

import lobby
import server_exceptions
import server_response

HOST = socket.gethostbyname(socket.gethostname())
PORT = 8888
BUFFER = 1024

connected_clients = []
running_lobby_threads = []

running_lobbies = {
    'main': (HOST, PORT),
}


"""
GENERAL PURPOSE MESSAGES
"""

joining_msg = "[Lobby] You joined the main lobby!\n[Lobby] Use !help to see a list of commands."
exit_msg = "[Lobby] Closing connection..."

help_msg = ("[help] List of commands to use in this lobby.\n!help\t\t\t\t\t:\tlists all available commands."
            "\n!join [lobby name]\t\t:\tconnects you to another lobby."
            "\n!create [lobby name]\t:\tcreates new lobby."
            "\n!lobbies\t\t\t\t:\tlists all available lobbies.")


def check_running_lobbies(lobby_data):
    """
    checks if lobby_data already exists
    :param lobby_data:
    :return:
    """
    lobby_exists = False
    for lobby_name in running_lobbies:
        # iterates through running_lobbies vector
        if running_lobbies[lobby_name] == lobby_data or lobby_name == lobby_data:
            # checks if the lobby already exists in the vector.
            lobby_exists = True
            break
    return lobby_exists


def join_lobby(lobby_host, lobby_port):
    try:
        if not check_running_lobbies((lobby_host, lobby_port)):
            raise server_exceptions.LobbyError("[join_lobby] couldn't find any running lobby with that data.")
        response = server_response.generate_response(2, HOST, connection=[lobby_host, lobby_port])
        return response
    except server_exceptions.LobbyError:
        return


def create_lobby(lobby_name, creator_client):
    """
    Creates a lobby object using the given information
    :param lobby_name: string
    :param creator_client: tuple containing client socket and addr.
    :return:
    """
    new_lobby = lobby.Lobby(
        name=lobby_name,
        creator=creator_client
    )
    # lobby thread
    lobby_thread = threading.Thread(target=new_lobby.create_lobby)
    lobby_thread.start()

    # running lobby thread vector
    running_lobby_threads.append(lobby_thread)

    # running lobbies : name -> Host, Port
    running_lobbies[lobby_name] = (new_lobby.HOST, new_lobby.PORT)

    return new_lobby.HOST, new_lobby.PORT


def handle_lobby_commands(cmd, client_data, client_is_running):
    """
    Handles the commands received by the client handler and
    creates a response accordingly.
    :param client_is_running: asyncio event
    :param cmd: command
    :param client_data: tuple containing client socket and addr.
    :return: response (decoded)
    """
    def join():
        if not check_running_lobbies(cmd[1]):
            return server_response.generate_response(3, HOST, msg="Could not find lobby.")
        client_is_running.set()
        lobby_host, lobby_port = running_lobbies[cmd[1]]
        return join_lobby(lobby_host, lobby_port)

    def create():
        if not check_running_lobbies(cmd[1]):
            # checks if lobby already exists.
            lobby_host, lobby_port = create_lobby(cmd[1], client_data)
            client_is_running.set()
            return join_lobby(lobby_host, lobby_port)

    # separates the received command into small pieces
    cmd = cmd.split(' ')

    print("[DEBUG - handle_lobby_commands] - " + str(cmd))

    # declaration of the response dictionary
    response = server_response.generate_response(3, HOST, msg="Unknown command.")

    try:
        # try to identify the first command.
        match cmd[0]:
            case "!help":
                #                          #
                #    sends command list    #
                #                          #

                response = server_response.generate_response(1, HOST, msg=help_msg)

            case "!exit":
                #                         #
                #    closes connection    #
                #                         #
                response = server_response.generate_response(5, HOST, msg=exit_msg)
                client_is_running.set()

            case "!join":
                #                         #
                #   joins another lobby   #
                #                         #

                if not len(cmd) == 2:
                    raise server_exceptions.CmdSetError(f"[handle_lobby_commands] Not enough parameters found.\n"
                                                        f"[handle_lobby_commands] Expected 1, but given {len(cmd) - 1}.")
                response = join()

            case "!create":
                #                          #
                #    creates a new lobby   #
                #                          #

                if not len(cmd) == 2:
                    raise server_exceptions.CmdSetError(f"[handle_lobby_commands] Not enough parameters found.\n"
                                                        f"[handle_lobby_commands] Expected 1, but given {len(cmd) - 1}.")
                response = create()

    except server_exceptions.CmdSetError as parameter_exception:
        print(parameter_exception)

    return json.dumps(response).encode()


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
    """
    handles the client:
     - receives data / commands
     - gracefully shuts down client after receiving !exit command.
     - handles commands with handle_lobby_commands() function
     - sends response to the client.
    :param client:
    :param addr:
    :return:
    """
    loop = asyncio.get_event_loop()

    # send join message #
    join_response = server_response.generate_response(1, HOST, msg=joining_msg)
    join_msg = json.dumps(join_response).encode()

    await loop.sock_sendto(client, join_msg, addr)

    client_is_running = asyncio.Event()

    # receive data from the connected client
    while not client_is_running.is_set():
        data = b""

        # Second while-loop to receive larger data  (keyword buffer size)
        while True:
            # receives data with size of BUFFER
            recv_data = (await loop.sock_recv(client, BUFFER))
            data += recv_data
            if len(recv_data) < BUFFER:
                # Breaks the second while-loop if the received data is smaller than the buffer.
                break

        # Decode fully received data block.
        data = data.decode()

        if data == "!exit":
            break

        # handles lobby commands
        response = handle_lobby_commands(data, (client, addr), client_is_running)

        # sends a response in form of a hashmap (code, host, {keyword-arguments})
        await loop.sock_sendto(client, response, addr)

    print(f"[handle_client] closing client connection with {addr[0]}")
    client.close()
    connected_clients.remove((client, addr))


async def run_server():
    """
    Creates a server socket and handles starts the handle_client and client acceptation loop
    :return:
    """
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

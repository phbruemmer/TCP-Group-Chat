import threading

import server_response

import asyncio
import random
import socket
import json
import ports


def port_is_open(host, port, timeout=5):
    try:
        with socket.create_connection((host, port), timeout):
            return True
    except (socket.timeout, ConnectionRefusedError):
        return False


def get_open_port(HOST):
    """
    checks for open ports.
    :return: int -> open port
    """
    port_range_start = 10000
    port_range_end = 20000

    random_port = random.randint(port_range_start, port_range_end)

    while random_port in ports.blocked_ports or threading.Thread(target=port_is_open, args=(HOST, random_port)).start():
        random_port = random.randint(port_range_start, port_range_end)
    ports.blocked_ports.append(random_port)
    return random_port


class Lobby:
    # Constant Variables
    HOST = socket.gethostbyname(socket.gethostname())
    PORT = get_open_port(HOST)
    BUFFER = 1024

    # Dynamic Variables
    connected_clients = []      # contains tuples (client_sock, addr)
    running = True              # changes when the server stops running
    password = ""

    user_counter = 0

    stop_event = asyncio.Event()

    def __init__(self, name, creator):
        self.name = name        # Name of the new lobby
        self.creator = creator  # creator is a tuple containing the ip and port of the client

    def create_lobby(self):
        asyncio.run(self.lobby_setup())

    def close(self):
        # Sets the stop_event to stop the infinite loop.
        self.stop_event.set()

        # Resets the password
        self.password = ""

        # connects a dummy to skip the await loop.sock_accept() function.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as dummy:
            dummy.connect((self.HOST, self.PORT))
            dummy.close()

    async def send_all(self, loop, client_data, data):
        """
        sends data to all clients in the connected clients list.
        :param loop: current event loop
        :param client_data: tuple containing client socket and address
        :param data: encrypted data to send to other clients
        :return: -
        """
        for receiver_clients in self.connected_clients:
            if not receiver_clients == client_data:
                await loop.sock_sendto(receiver_clients[0], data, receiver_clients[1])

    async def handle_client(self, client, addr, **kwargs):
        """
        manages the connected clients.
        - handles commands
        - normal messages are sent to all connected clients in this lobby.
        :param client: client socket
        :param addr: address
        :return: -
        """
        async def receive_full_msg() -> str:
            f_data = b""
            while True:                                                 # loop to assemble larger messages
                f_data += await loop.sock_recv(client, self.BUFFER)
                if len(f_data) < self.BUFFER:                           # if message is smaller than the buffer, break
                    break
            return f_data.decode()

        async def client_loop():
            while True:  # loop to receive incoming messages
                data = await receive_full_msg()
                if data == "!leave" or data == "!exit":  # if message !leave or !exit, disconnect the client.
                    break
                # send message to all clients connected to this lobby
                if (client, addr) == admin and data.startswith('!'):
                    await handle_superuser_commands(data)
                else:
                    data = username + " >> " + data
                    response = server_response.generate_response(1, host=self.HOST, msg=data)
                    serialized_response = json.dumps(response).encode()
                    await self.send_all(loop, (client, addr), serialized_response)

        async def check_password():
            if not self.password == "":
                password_query = server_response.generate_response(1, self.HOST, msg="Enter Lobby password:")
                serialized_query = json.dumps(password_query).encode()
                await loop.sock_sendto(client, serialized_query, addr)
                password = await receive_full_msg()
                if not password == self.password:
                    pw_response = server_response.generate_response(1, self.HOST,
                                                                    msg="Invalid password. Closing connection.")
                    s_query = json.dumps(pw_response).encode()
                    await loop.sock_sendto(client, s_query, addr)
                    client.close()
                    return False
            return True

        async def handle_superuser_commands(command):
            command = command.split(" ")

            match command[0]:
                case "!set_password":
                    if len(command) == 2:
                        self.password = command[1]
                case "!kickall":
                    self.stop_event.set()

        username = kwargs.get("username", "")

        loop = asyncio.get_event_loop()
        admin = self.connected_clients[0]                           # The first client is always the admin

        # Check lobby password
        if not await check_password():
            return

        connected = server_response.generate_response(1, self.HOST, msg=f"You successfully connected to {self.name}")
        s_connected = json.dumps(connected).encode()
        await loop.sock_sendto(client, s_connected, addr)

        # Starts the client loop to receive and send data.
        await client_loop()

        # disconnect the client and remove it from the connected clients list.
        client.close()
        self.connected_clients.remove((client, addr))

        if len(self.connected_clients) == 0:
            self.close()

    async def lobby_setup(self):
        def lobby_loop():
            print(f"[lobby_setup] {addr} joined '{self.name}'.")
            self.connected_clients.append((client, addr))
            loop.create_task(self.handle_client(client, addr, username=f"user-{self.user_counter}"))
            self.user_counter += 1
        print(f"[lobby_setup] creating new lobby on port {self.PORT} ...")

        # TCP server socket setup
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.HOST, self.PORT))
        server.listen(8)
        server.setblocking(False)

        print(f"[lobby_setup] new lobby ({self.name} by '{self.creator[0]}') successfully created on port {self.PORT}.")

        # Get event loop
        loop = asyncio.get_event_loop()

        # handle incoming client connection
        while not self.stop_event.is_set():
            client, addr = await loop.sock_accept(server)
            if self.stop_event.is_set():
                break
            lobby_loop()

        print(f"[lobby_setup] closing lobby server ('{self.name}')...")
        server.close()
        ports.blocked_ports.remove(self.PORT)

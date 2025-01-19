import server_response
import ports

import asyncio
import socket
import json


class Lobby:
    # Constant Variables
    HOST = socket.gethostbyname(socket.gethostname())
    PORT = ports.get_open_port(HOST)
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

    def create_lobby(self) -> None:
        """
        method to start the lobby.
        :return: -
        """
        asyncio.run(self.lobby_setup())

    def close(self) -> None:
        """
        closes the server.
        :return: -
        """
        # Sets the stop_event to stop the infinite loop.
        self.stop_event.set()

        # Resets the password
        self.password = ""

        # connects a dummy to skip the await loop.sock_accept() function.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as dummy:
            dummy.connect((self.HOST, self.PORT))
            dummy.close()

    async def send_all(self, loop, client, addr, data) -> None:
        """
        sends data to all clients in the connected clients list.
        :param loop: current event loop
        :param client: socket client object
        :param addr: client address
        :param data: message (decrypted)
        :return: -
        """
        for receiver_clients in self.connected_clients:
            if not receiver_clients == (client, addr):
                await self.send_to(loop, receiver_clients[0], receiver_clients[1], data)

    async def send_to(self, loop, client, addr, data) -> None:
        """
        Formats and sends data to the client according to the protocol (json-format).
        ! Only for messages !
        :param loop: current event loop
        :param client: socket client object
        :param addr: client address
        :param data: message (decrypted)
        :return: -
        """
        message = server_response.generate_response(1, self.HOST, msg=data)
        serialized_msg = json.dumps(message).encode()
        await loop.sock_sendto(client, serialized_msg, addr)

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
            """
            receives and reassembles buffered data from the client.
            :return: string
            """
            f_data = b""
            while True:                                                 # loop to assemble larger messages
                f_data += await loop.sock_recv(client, self.BUFFER)
                if len(f_data) < self.BUFFER:                           # if message is smaller than the buffer, break
                    break
            return f_data.decode()

        async def client_loop() -> None:
            """
            Handles the incoming data stream from the client.
            :return: -
            """
            # loop to receive incoming messages
            while True:
                data = await receive_full_msg()
                if data == "!exit":
                    # !exit closes the connection between client and server and stops the client loop.
                    break

                # checks if client is admin and if the received message starts with '!'
                if (client, addr) == admin and data.startswith('!'):
                    # handles admin commands
                    await handle_superuser_commands(data)
                else:
                    # sends message to all clients connected to this lobby
                    await self.send_all(loop, client, addr, username + " >> " + data)

        async def check_password() -> bool:
            """
            Checks the lobby password.
            :return: bool
            """
            # Checks if the admin set a password for the lobby.
            if not self.password == "":
                # generates password query
                password_query = server_response.generate_response(1, self.HOST, msg="Enter Lobby password:")
                serialized_query = json.dumps(password_query).encode()

                # Sends password query to the client
                await loop.sock_sendto(client, serialized_query, addr)

                # Waits for client response
                password = await receive_full_msg()

                # Checks if client response matches lobby password
                if not password == self.password:
                    # If the client entered the wrong password, the connection closes.
                    await self.send_to(loop, client, addr, "Invalid password. Closing connection.")
                    client.close()
                    return False
            return True

        async def handle_superuser_commands(command) -> None:
            """
            Executes the corresponding command after separating the command into smaller pieces.
            :param command: string
            :return:
            """
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

        # Sends success message
        await self.send_to(loop, client, addr, f"You successfully connected to {self.name}")

        # Starts the client loop to receive and send data.
        await client_loop()

        # disconnect the client and remove it from the connected clients list.
        client.close()
        self.connected_clients.remove((client, addr))

        if len(self.connected_clients) == 0:
            self.close()

    async def lobby_setup(self) -> None:
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

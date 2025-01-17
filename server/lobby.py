import server_response

import asyncio
import random
import socket
import json
import ports


def get_open_port():
    """
    checks for open ports.
    :return: int -> open port
    """
    port_range_start = 10000
    port_range_end = 20000

    random_port = random.randint(port_range_start, port_range_end)

    while random_port in ports.blocked_ports:
        random_port = random.randint(port_range_start, port_range_end)
    ports.blocked_ports.append(random_port)
    return random_port


class Lobby:
    # Constant Variables
    HOST = socket.gethostbyname(socket.gethostname())
    PORT = get_open_port()
    BUFFER = 1024

    # Dynamic Variables
    connected_clients = []      # contains tuples (client_sock, addr)
    running = True              # changes when the server stops running

    stop_event = asyncio.Event()

    def __init__(self, name, creator):
        self.name = name        # Name of the new lobby
        self.creator = creator  # creator is a tuple containing the ip and port of the client

    def create_lobby(self):
        asyncio.run(self.lobby_setup())

    def close(self):
        # Sets the stop_event to stop the infinite loop.
        self.stop_event.set()

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

    async def handle_client(self, client, addr):
        """
        manages the connected clients.
        - handles commands
        - normal messages are sent to all connected clients in this lobby.
        :param client: client socket
        :param addr: address
        :return: -
        """
        loop = asyncio.get_event_loop()

        while True:                                                 # loop to receive incoming messages
            data = b""
            while True:                                             # loop to assemble larger messages
                data += await loop.sock_recv(client, self.BUFFER)
                if len(data) < self.BUFFER:                         # if message is smaller than the buffer, break
                    break
            data = data.decode()
            if data == "!leave" or data == "!exit":                 # if message !leave or !exit, disconnect the client.
                break
            # send message to all clients connected to this lobby
            print(data)
            response = server_response.generate_response(1, host=self.HOST, msg=data)
            serialized_response = json.dumps(response).encode()
            await self.send_all(loop, (client, addr), serialized_response)
        # LOOP - END #
        # disconnect the client and remove it from the connected clients list.
        client.close()
        self.connected_clients.remove((client, addr))

        if len(self.connected_clients) == 0:
            self.close()

    async def lobby_setup(self):
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
            print(f"[lobby_setup] {addr} joined '{self.name}'.")
            self.connected_clients.append((client, addr))
            loop.create_task(self.handle_client(client, addr))
        print(f"[lobby_setup] closing lobby server ('{self.name}')...")
        server.close()
        ports.blocked_ports.remove(self.PORT)


if __name__ == '__main__':
    lobby = Lobby('epic lobby', ("robert", "Diidn"))
    lobby.create_lobby()


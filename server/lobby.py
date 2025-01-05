import asyncio
import random
import socket
import ports


def get_open_port():
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

    def __init__(self, name, creator):
        self.name = name        # Name of the new lobby
        self.creator = creator  # creator is a tuple containing the ip and port of the client

    def create_lobby(self):
        asyncio.run(self.lobby_setup())

    async def send_all(self, loop, client_data, data):
        for receiver_clients in self.connected_clients:
            if not receiver_clients == client_data:
                await loop.sock_sendto(receiver_clients[0], data, receiver_clients[1])

    async def handle_client(self, client, addr):
        loop = asyncio.get_event_loop()

        while True:                                                 # loop to receive incoming messages
            data = b""
            while True:                                             # loop to assembly larger messages
                data += await loop.sock_recv(client, self.BUFFER)
                if len(data) < self.BUFFER:                         # if message is smaller than the buffer, break
                    break
            data = data.decode()
            if data == "!leave" or data == "!exit":                 # if message !leave or !exit, disconnect the client.
                break
            print(data)
            # send message to all clients connected to this lobby
            await self.send_all(loop, (client, addr), data.encode())
        # LOOP - END #
        # disconnect the client and remove it from the connected clients list.
        client.close()
        self.connected_clients.remove((client, addr))
        if len(self.connected_clients) == 0:
            self.running = False

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
        while True:
            client, addr = await loop.sock_accept(server)
            print(f"[lobby_setup] {addr} joined '{self.name}'.")
            self.connected_clients.append((client, addr))
            loop.create_task(self.handle_client(client, addr))
            if not self.running:
                break

        print(f"[lobby_setup] closing lobby server ('{self.name}')...")
        server.close()
        ports.blocked_ports.remove(self.PORT)


if __name__ == '__main__':
    lobby = Lobby('epic lobby', ("robert", "Diidn"))
    lobby.create_lobby()


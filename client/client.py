import asyncio
import socket
import json


class ConnectionData:
    HOST = "192.168.115.200"
    PORT = 8888
    BUFFER = 1024


change_server_event = asyncio.Event()
connection_data = ConnectionData()


def handle_response(response, stop_event) -> None:
    """
    handles responses from the server.
    :param response: str
    :param stop_event: asyncio.Event()
    :return: -
    """
    response_code = response['code']
    response_host = response['host']

    try:
        match response_code:
            case 1:
                # Normal message from the server
                value = response['msg']
                print(value)
            case 2:
                # change server
                new_lobby_data = response['connection']

                lobby_host = new_lobby_data[0]
                lobby_port = new_lobby_data[1]

                connection_data.HOST = lobby_host
                connection_data.PORT = lobby_port

                change_server_event.set()
                stop_event.set()
            case 3:
                # Client side error - Not Found
                pass
            case 4:
                # Serverside error
                pass
            case 5:
                # Close connection
                stop_event.set()
    except KeyError:
        pass
        # print("[handle_response] incorrect response.")


async def receiver(client, stop_event) -> None:
    """
    handles incoming data from the server.
    :param client: socket client object
    :param stop_event: asyncio.Event()
    :return: -
    """
    def receive() -> str:
        """
        receives full transmission from the server.
        :return: str
        """
        data = b""
        while True:
            recv_data = client.recv(connection_data.BUFFER)
            data += recv_data
            # Breaks the loop after receiving data smaller than the buffer
            if len(recv_data) < connection_data.BUFFER:
                break
        return data.decode()

    try:
        while not stop_event.is_set():
            try:
                command_map = json.loads(receive())
                handle_response(command_map, stop_event)
            except BlockingIOError:
                await asyncio.sleep(0)
                continue
            except json.JSONDecodeError:
                print("[receiver] Invalid format.")
                continue
    except asyncio.CancelledError:
        print("[receiver] stopping receiver task.")
    except Exception as e:
        print(f"[receive] unexpected error: {e}")
        raise


async def sender(client, stop_event):
    """
    sends user input to the server.
    :param client: socket client object
    :param stop_event: asyncio.Event()
    :return: -
    """

    try:
        while not stop_event.is_set():
            # small sleep to prevent busy looping
            await asyncio.sleep(0.1)

            try:
                msg = await asyncio.to_thread(input)
                client.send(msg.encode())
                if msg == "!exit":
                    stop_event.set()
            except EOFError:
                stop_event.set()
    except asyncio.CancelledError:
        print("[sender] stopping sender task.")
    except Exception as e:
        print(f"[sender] Unexpected error: {e}")
        raise


async def handle_client(client):
    """
    function to handle asynchronous sending and receiving tasks.
    :param client: socket client object
    :return: -
    """
    stop_event = asyncio.Event()

    receive = asyncio.create_task(receiver(client, stop_event))
    send = asyncio.create_task(sender(client, stop_event))

    try:
        await asyncio.wait([receive, send], return_when=asyncio.FIRST_COMPLETED)
    except Exception as e:
        print(f"[handle_client] Unexpected error: {e}")
        raise
    finally:
        receive.cancel()
        send.cancel()
        await asyncio.gather(receive, send, return_exceptions=True)
        print("[handle_client] successfully stopped the send and receive coroutines.")


def start_client():
    """
    Prepares the client for server connection.
    :return:
    """
    # clear asyncio event
    change_server_event.clear()

    print(f"[start_client] connecting to {connection_data.HOST} on port {connection_data.PORT}.")
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((connection_data.HOST, connection_data.PORT))
        client.setblocking(False)
        asyncio.run(handle_client(client))
        client.close()
    except Exception as e:
        print(f"[start_client] Unexpected error: {e}")
        raise


def client_loop():
    change_server_event.set()

    while change_server_event.is_set():
        start_client()


if __name__ == '__main__':
    client_loop()


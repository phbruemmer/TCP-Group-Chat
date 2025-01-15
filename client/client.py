import threading
import asyncio
import socket
import json


HOST = "192.168.115.200"
PORT = 8888
BUFFER = 1024


def handle_response(response, stop_event):
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
                print(new_lobby_data)
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


async def receiver(client, stop_event):
    try:
        while not stop_event.is_set():
            data = b""
            try:
                while True:
                    recv_data = client.recv(BUFFER)
                    data += recv_data
                    if len(recv_data) < BUFFER:
                        break
                command_map = json.loads(data.decode())
                handle_response(command_map, stop_event)
            except BlockingIOError:
                await asyncio.sleep(0)
                continue
            except json.JSONDecodeError:
                continue
    except asyncio.CancelledError:
        print("[receiver] stopping receiver task.")
    except Exception as e:
        print(f"[receive] unexpected error: {e}")
        raise


async def sender(client, stop_event):
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
    print(f"[start_client] connecting to {HOST} on port {PORT}.")
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((HOST, PORT))
        client.setblocking(False)
        asyncio.run(handle_client(client))
        client.close()
    except Exception as e:
        print(f"[start_client] Unexpected error: {e}")
        raise


if __name__ == '__main__':
    start_client()


import asyncio
import socket


HOST = "192.168.115.200"
PORT = 8888
BUFFER = 1024


async def receiver(client):
    data = None
    try:
        while not data == b"[Lobby] Closing connection...":
            data = b""
            while True:
                recv_data = client.recv(BUFFER)
                data += recv_data
                if len(recv_data) < BUFFER:
                    break
            print(data.decode())
            await asyncio.sleep(0)
    except asyncio.CancelledError:
        print("[receiver] stopping receiver task.")
    except Exception as e:
        print(f"[receive] unexpected error: {e}")
        raise


async def sender(client):
    loop = asyncio.get_event_loop()
    try:
        while True:
            msg = await loop.run_in_executor(None, input, ">>>")
            print(msg)
            await client.send(msg.encode())
    except asyncio.CancelledError:
        print("[sender] stopping sender task.")
    except Exception as e:
        print(f"[sender] Unexpected error: {e}")
        raise


async def handle_client(client):
    receive = asyncio.create_task(receiver(client))
    # print(f"[handle_client] created receive task: {receive}")
    send = asyncio.create_task(sender(client))
    # print(f"[handle_client] created send task: {send}")

    try:
        await asyncio.wait([receive, send], return_when=asyncio.FIRST_EXCEPTION)
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
        asyncio.run(handle_client(client))
        client.close()
    except Exception as e:
        print(f"[start_client] Unexpected error: {e}")
        raise


if __name__ == '__main__':
    start_client()


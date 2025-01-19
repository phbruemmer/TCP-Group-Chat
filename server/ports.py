from server import PORT

import threading
import socket
import random

blocked_ports = [PORT]


def port_is_open(host, port, timeout=5) -> bool:
    """
    Checks if a port is open or closed.
    :param host: str
    :param port: int
    :param timeout: int
    :return: bool
    """
    try:
        with socket.create_connection((host, port), timeout):
            return True
    except (socket.timeout, ConnectionRefusedError):
        return False


def get_open_port(HOST) -> int:
    """
    checks for open ports.
    :return: int -> open port
    """
    port_range_start = 10000
    port_range_end = 20000

    random_port = random.randint(port_range_start, port_range_end)

    while random_port in blocked_ports or threading.Thread(target=port_is_open, args=(HOST, random_port)).start():
        random_port = random.randint(port_range_start, port_range_end)
    blocked_ports.append(random_port)
    return random_port

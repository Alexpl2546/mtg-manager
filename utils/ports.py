import random
import socket

from utils.storage import load_clients, load_settings

PORT_RANGE_START = 1024
PORT_RANGE_END = 65535

RESERVED_PORTS = {
    1, 2, 3, 4, 5, 6, 7, 9, 13, 17, 19, 20, 21, 22, 23, 25,
    37, 42, 43, 49, 53, 67, 68, 69, 70, 79, 80, 81, 88,
    109, 110, 111, 113, 119, 123, 135, 137, 138, 139, 143,
    161, 162, 179, 194, 389, 443, 445, 465, 514, 587, 631,
    636, 873, 993, 995, 1080,
    1433, 1521, 1723, 1883,
    2049, 2375, 2376,
    3128, 3129, 3130,
    3306, 3389, 5432, 5900, 6379,
    8080, 8443,
}


def is_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def get_reserved_ports_from_settings() -> set[int]:
    settings = load_settings()
    reserved = set()

    telemt_port = settings.get("telemt", {}).get("port")
    http_port = settings.get("http", {}).get("port")
    socks5_port = settings.get("socks5", {}).get("port")

    for port in (telemt_port, http_port, socks5_port):
        if isinstance(port, int):
            reserved.add(port)

    return reserved


def get_used_mtg_ports() -> set[int]:
    clients = load_clients("mtg")
    used = set()

    for client in clients.values():
        port = client.get("port")
        if isinstance(port, int):
            used.add(port)

    return used


def get_free_mtg_port() -> int:
    reserved_ports = RESERVED_PORTS | get_reserved_ports_from_settings()
    used_ports = get_used_mtg_ports()

    for _ in range(2000):
        port = random.randint(PORT_RANGE_START, PORT_RANGE_END)

        if port in reserved_ports:
            continue

        if port in used_ports:
            continue

        if not is_port_free(port):
            continue

        return port

    raise RuntimeError("Не удалось подобрать свободный порт для MTProto")

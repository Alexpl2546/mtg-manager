import secrets
from datetime import datetime

from providers.base import BaseProvider
from utils.storage import load_clients, load_settings, save_clients
from utils.threeproxy import sync_3proxy


class HTTPProvider(BaseProvider):
    protocol = "http"

    def create_client(self, name: str) -> dict:
        clients = load_clients(self.protocol)
        settings = load_settings()

        if name in clients:
            raise ValueError(f"Клиент '{name}' уже существует")

        client = {
            "name": name,
            "username": f"http_{name}",
            "password": secrets.token_urlsafe(12),
            "host": settings["http"]["host"],
            "port": settings["http"]["port"],
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

        clients[name] = client
        try:
            save_clients(self.protocol, clients)
            sync_3proxy()
        except Exception:
            clients.pop(name, None)
            save_clients(self.protocol, clients)
            raise
        return client

    def delete_client(self, name: str) -> dict:
        clients = load_clients(self.protocol)

        if name not in clients:
            raise ValueError(f"Клиент '{name}' не найден")

        client = clients[name]
        del clients[name]
        try:
            save_clients(self.protocol, clients)
            sync_3proxy()
        except Exception:
            clients[name] = client
            save_clients(self.protocol, clients)
            raise
        return client

    def get_client(self, name: str) -> dict | None:
        return load_clients(self.protocol).get(name)

    def list_clients(self) -> dict:
        return load_clients(self.protocol)

import json
import os
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from providers.base import BaseProvider
from utils.storage import load_clients, load_settings, save_clients

TELEMT_API_URL = os.getenv("TELEMT_API_URL", "http://127.0.0.1:9091").rstrip("/")
TELEMT_API_AUTH = os.getenv("TELEMT_API_AUTH", "").strip()


class TelemtProvider(BaseProvider):
    protocol = "telemt"

    def _request(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
    ) -> dict:
        headers = {"Accept": "application/json"}
        if TELEMT_API_AUTH:
            headers["Authorization"] = TELEMT_API_AUTH

        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = Request(
            f"{TELEMT_API_URL}{path}",
            data=body,
            headers=headers,
            method=method,
        )

        try:
            with urlopen(request, timeout=20) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            response_text = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Telemt API вернул HTTP {exc.code}: {response_text}"
            ) from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Telemt API недоступен: {exc}") from exc

        if not data.get("ok"):
            error = data.get("error", {})
            message = error.get("message") or str(error) or "unknown error"
            raise RuntimeError(f"Telemt API: {message}")

        return data

    def health(self) -> dict:
        return self._request("GET", "/v1/health/ready").get("data", {})

    def remote_users(self) -> dict[str, dict]:
        response = self._request("GET", "/v1/users")
        users = response.get("data", [])
        return {
            item["username"]: item
            for item in users
            if isinstance(item, dict) and item.get("username")
        }

    def reconciliation_status(self) -> dict:
        local_users = set(load_clients(self.protocol))
        remote_users = set(self.remote_users())
        return {
            "local_count": len(local_users),
            "remote_count": len(remote_users),
            "missing_locally": sorted(remote_users - local_users),
            "missing_remotely": sorted(local_users - remote_users),
        }

    @staticmethod
    def _tls_link(user_data: dict) -> str | None:
        links = user_data.get("links", {})
        tls_links = links.get("tls") or []
        return tls_links[0] if tls_links else None

    def create_client(self, name: str) -> dict:
        clients = load_clients(self.protocol)
        settings = load_settings()

        if name in clients:
            raise ValueError(f"Клиент '{name}' уже существует")

        response = self._request("POST", "/v1/users", {"username": name})
        response_data = response.get("data", {})
        user_data = response_data.get("user", {})
        secret = response_data.get("secret")

        if not secret:
            raise RuntimeError("Telemt API не вернул секрет нового пользователя")

        client = {
            "name": name,
            "secret": secret,
            "port": settings["telemt"]["port"],
            "domain": settings["telemt"]["domain"],
            "tg_url": self._tls_link(user_data),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        clients[name] = client
        try:
            save_clients(self.protocol, clients)
        except Exception:
            try:
                self._request("DELETE", f"/v1/users/{quote(name, safe='')}")
            except Exception:
                pass
            raise
        return client

    def delete_client(self, name: str) -> dict:
        clients = load_clients(self.protocol)

        if name not in clients:
            raise ValueError(f"Клиент '{name}' не найден")

        client = clients[name]
        self._request("DELETE", f"/v1/users/{quote(name, safe='')}")

        del clients[name]
        try:
            save_clients(self.protocol, clients)
        except Exception as exc:
            raise RuntimeError(
                "Пользователь удалён из Telemt, но локальная база не обновилась. "
                "Требуется reconciliation."
            ) from exc
        return client

    def get_client(self, name: str) -> dict | None:
        return load_clients(self.protocol).get(name)

    def list_clients(self) -> dict:
        return load_clients(self.protocol)

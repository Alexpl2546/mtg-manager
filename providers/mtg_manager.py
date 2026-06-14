import subprocess
from datetime import datetime
from pathlib import Path

from providers.base import BaseProvider
from utils.ports import get_free_mtg_port
from utils.storage import load_clients, load_settings, save_clients

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPT_PATH = BASE_DIR / "scripts" / "install-mtproto.sh"
DELETE_SCRIPT_PATH = BASE_DIR / "scripts" / "delete-mtproto.sh"


class MTGProvider(BaseProvider):
    protocol = "mtg"

    def create_client(self, name: str) -> dict:
        clients = load_clients(self.protocol)
        settings = load_settings()

        if name in clients:
            raise ValueError(f"Клиент '{name}' уже существует")

        port = get_free_mtg_port()
        domain = settings["mtg"]["domain"]
        container_name = f"mtg-{name}"
        workdir = f"/opt/mtg-clients/{name}"

        result = subprocess.run(
            [
                "bash",
                str(SCRIPT_PATH),
                container_name,
                workdir,
                str(port),
                domain,
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Ошибка создания MTProto.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )

        parsed = {}
        for line in result.stdout.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                parsed[key.strip()] = value.strip()

        if parsed.get("STATUS") != "OK" or "TG_URL" not in parsed:
            raise RuntimeError(f"Неожиданный вывод скрипта:\n{result.stdout}")

        client = {
            "name": name,
            "container_name": parsed["CONTAINER"],
            "workdir": parsed["WORKDIR"],
            "port": int(parsed["PORT"]),
            "domain": parsed["DOMAIN"],
            "tg_url": parsed["TG_URL"],
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

        clients[name] = client
        save_clients(self.protocol, clients)
        return client

    def delete_client(self, name: str) -> dict:
        clients = load_clients(self.protocol)

        if name not in clients:
            raise ValueError(f"Клиент '{name}' не найден")

        client = clients[name]

        result = subprocess.run(
            [
                "bash",
                str(DELETE_SCRIPT_PATH),
                client["container_name"],
                client["workdir"],
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Ошибка удаления MTProto.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )

        del clients[name]
        save_clients(self.protocol, clients)
        return client

    def get_client(self, name: str) -> dict | None:
        return load_clients(self.protocol).get(name)

    def list_clients(self) -> dict:
        return load_clients(self.protocol)

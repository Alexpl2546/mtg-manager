from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from vpn_service.models import Protocol, Role, Server, User

BASE_DIR = Path(__file__).resolve().parent.parent


def _data_path() -> Path:
    return Path(os.getenv("VPN_SERVICE_DATA_PATH", BASE_DIR / "data" / "vpn_service.json"))


def _default_state() -> dict[str, Any]:
    return {
        "users": {
            "demo-user": asdict(
                User(
                    id="demo-user",
                    name="Александр",
                    telegram="@alexander",
                    role=Role.ADMIN,
                    email="alexander@example.com",
                )
            )
        },
        "servers": {
            "ru-1": asdict(
                Server(
                    id="ru-1",
                    name="Основной сервер",
                    location="RU",
                    protocols=(Protocol.VLESS, Protocol.AMNEZIAWG),
                    host=os.getenv("VPN_DEFAULT_HOST", "vpn.example.com"),
                )
            )
        },
        "devices": {},
        "configs": {},
    }


def _read_state() -> dict[str, Any]:
    data_path = _data_path()
    if not data_path.exists():
        return _default_state()

    try:
        content = data_path.read_text(encoding="utf-8").strip()
        if not content:
            return _default_state()
        state = json.loads(content)
    except (OSError, json.JSONDecodeError):
        return _default_state()

    default = _default_state()
    for key, value in default.items():
        state.setdefault(key, value)
    return state


def _write_state(state: dict[str, Any]) -> None:
    data_path = _data_path()
    data_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = data_path.with_suffix(data_path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary_path, data_path)


class JsonRepository:
    def state(self) -> dict[str, Any]:
        return _read_state()

    def save(self, state: dict[str, Any]) -> None:
        _write_state(state)

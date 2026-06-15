import json
import os
import threading
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

FILES = {
    "telemt": DATA_DIR / "telemt_clients.json",
    "http": DATA_DIR / "http_clients.json",
    "socks5": DATA_DIR / "socks5_clients.json",
    "settings": DATA_DIR / "settings.json",
}

_STORAGE_LOCK = threading.RLock()


def _read_json(path: Path, default: Any) -> Any:
    with _STORAGE_LOCK:
        if not path.exists():
            return default

        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return default

        return json.loads(text)


def _write_json(path: Path, data: Any) -> None:
    with _STORAGE_LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(path.suffix + ".tmp")
        temporary_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary_path, path)


def load_clients(protocol: str) -> dict:
    if protocol not in ("telemt", "http", "socks5"):
        raise ValueError(f"Unsupported protocol: {protocol}")
    return _read_json(FILES[protocol], {})


def save_clients(protocol: str, data: dict) -> None:
    if protocol not in ("telemt", "http", "socks5"):
        raise ValueError(f"Unsupported protocol: {protocol}")
    _write_json(FILES[protocol], data)


def load_settings() -> dict:
    return _read_json(FILES["settings"], {})


def save_settings(data: dict) -> None:
    _write_json(FILES["settings"], data)

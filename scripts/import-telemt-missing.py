#!/usr/bin/env python3
import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

PROJECT_DIR = Path(os.getenv("PROXY_MANAGER_DIR", "/opt/proxy-manager"))
CLIENTS_PATH = PROJECT_DIR / "data" / "telemt_clients.json"
SETTINGS_PATH = PROJECT_DIR / "data" / "settings.json"
CONFIG_PATH = Path(os.getenv("TELEMT_CONFIG_PATH", "/etc/telemt/telemt.toml"))
API_URL = os.getenv("TELEMT_API_URL", "http://127.0.0.1:9091").rstrip("/")
API_AUTH = os.getenv("TELEMT_API_AUTH", "").strip()

USER_LINE = re.compile(
    r'''^\s*(?:"([^"]+)"|'([^']+)'|([A-Za-z0-9_.-]+))\s*=\s*"([0-9a-fA-F]{32})"\s*(?:#.*)?$'''
)


def load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8") or "{}")
    if not isinstance(data, dict):
        raise RuntimeError(f"{path} must contain a JSON object")
    return data


def load_config_users(path: Path) -> dict[str, str]:
    users: dict[str, str] = {}
    in_users_section = False

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("[") and line.endswith("]"):
            in_users_section = line == "[access.users]"
            continue
        if not in_users_section or not line or line.startswith("#"):
            continue

        match = USER_LINE.fullmatch(raw_line)
        if match:
            username = next(value for value in match.groups()[:3] if value)
            users[username] = match.group(4).lower()

    return users


def api_user(username: str) -> dict:
    headers = {"Accept": "application/json"}
    if API_AUTH:
        headers["Authorization"] = API_AUTH

    request = Request(
        f"{API_URL}/v1/users/{quote(username, safe='')}",
        headers=headers,
    )
    with urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if not payload.get("ok"):
        raise RuntimeError(f"Telemt API error for {username}: {payload.get('error')}")
    return payload.get("data", {})


def first_tls_link(user_data: dict) -> str | None:
    links = user_data.get("links", {}).get("tls") or []
    return links[0] if links else None


def atomic_write(path: Path, data: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.chmod(temporary, path.stat().st_mode)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import Telemt users missing from Proxy Manager without rotating secrets."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write imported records. Without this flag the command is read-only.",
    )
    args = parser.parse_args()

    clients = load_json(CLIENTS_PATH)
    settings = load_json(SETTINGS_PATH)
    config_users = load_config_users(CONFIG_PATH)
    missing = sorted(set(config_users) - set(clients))

    if not missing:
        print("No missing Telemt users")
        return 0

    print("Users to import:", ", ".join(missing))
    imported = {}

    for username in missing:
        remote = api_user(username)
        if not remote.get("in_runtime", False):
            raise RuntimeError(f"Telemt user is not active in runtime: {username}")

        imported[username] = {
            "name": username,
            "secret": config_users[username],
            "port": settings["telemt"]["port"],
            "domain": settings["telemt"]["domain"],
            "tg_url": first_tls_link(remote),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "imported_from": "telemt.toml",
        }

    if not args.apply:
        print("Dry run completed. Re-run with --apply to write records.")
        return 0

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = CLIENTS_PATH.with_name(f"telemt_clients.json.before-import-{timestamp}")
    shutil.copy2(CLIENTS_PATH, backup)

    clients.update(imported)
    atomic_write(CLIENTS_PATH, clients)

    print(f"Imported users: {len(imported)}")
    print(f"Backup: {backup}")
    print("Secrets and links were preserved; no Telemt users were modified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

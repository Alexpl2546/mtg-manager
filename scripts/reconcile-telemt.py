#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen

PROJECT_DIR = Path(os.getenv("PROXY_MANAGER_DIR", "/opt/proxy-manager"))
CLIENTS_PATH = PROJECT_DIR / "data" / "telemt_clients.json"
API_URL = os.getenv("TELEMT_API_URL", "http://127.0.0.1:9091").rstrip("/")
API_AUTH = os.getenv("TELEMT_API_AUTH", "").strip()


def load_local_users() -> set[str]:
    if not CLIENTS_PATH.exists():
        return set()
    data = json.loads(CLIENTS_PATH.read_text(encoding="utf-8") or "{}")
    if not isinstance(data, dict):
        raise RuntimeError(f"{CLIENTS_PATH} must contain a JSON object")
    return set(data)


def load_remote_users() -> set[str]:
    headers = {"Accept": "application/json"}
    if API_AUTH:
        headers["Authorization"] = API_AUTH

    request = Request(f"{API_URL}/v1/users", headers=headers)
    with urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if not payload.get("ok"):
        raise RuntimeError(f"Telemt API error: {payload.get('error')}")

    return {
        item["username"]
        for item in payload.get("data", [])
        if isinstance(item, dict) and item.get("username")
    }


def main() -> int:
    local_users = load_local_users()
    remote_users = load_remote_users()
    missing_locally = sorted(remote_users - local_users)
    missing_remotely = sorted(local_users - remote_users)

    print(f"Local users: {len(local_users)}")
    print(f"Telemt users: {len(remote_users)}")
    print("Missing locally:", ", ".join(missing_locally) or "none")
    print("Missing remotely:", ", ".join(missing_remotely) or "none")

    if missing_locally:
        print(
            "NOTE: Existing Telemt secrets cannot be recovered through the list API. "
            "These users were not imported or rotated."
        )

    return 1 if missing_locally or missing_remotely else 0


if __name__ == "__main__":
    sys.exit(main())

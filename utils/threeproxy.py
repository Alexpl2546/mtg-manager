import shutil
import subprocess
from pathlib import Path

from utils.storage import load_clients, load_settings

THREEPROXY_CONFIG = Path("/etc/3proxy/3proxy.cfg")
THREEPROXY_BACKUP = Path("/etc/3proxy/3proxy.cfg.bak")
THREEPROXY_SERVICE = "3proxy"


def _escape_password(password: str) -> str:
    return password.replace(" ", "_")


def _collect_users():
    http_clients = load_clients("http")
    socks5_clients = load_clients("socks5")

    users = {}

    for source in (http_clients, socks5_clients):
        for client in source.values():
            username = client["username"]
            password = client["password"]

            if username in users and users[username] != password:
                raise RuntimeError(
                    f"Конфликт логинов 3proxy: пользователь '{username}' "
                    "уже существует с другим паролем"
                )
            users[username] = password

    return http_clients, socks5_clients, users


def build_3proxy_config() -> str:
    settings = load_settings()
    http_clients, socks5_clients, users = _collect_users()

    http_port = settings["http"]["port"]
    socks5_port = settings["socks5"]["port"]

    lines = [
        "daemon",
        "maxconn 100",
        "nserver 1.1.1.1",
        "nserver 8.8.8.8",
        "nscache 65536",
        "timeouts 1 5 30 60 180 1800 15 60",
        "",
        "log /var/log/3proxy/3proxy.log",
        'logformat "L%d-%m-%Y %H:%M:%S %U %C:%c %R:%r %O %I %T"',
        "",
    ]

    if users:
        user_parts = [
            f"{username}:CL:{_escape_password(password)}"
            for username, password in sorted(users.items())
        ]
        lines.append("users " + " ".join(user_parts))
        lines.append("auth strong")
        lines.append("")
    else:
        lines.append("users dummy:CL:dummy_password")
        lines.append("auth strong")
        lines.append("deny *")
        lines.append("")

    http_usernames = sorted(client["username"] for client in http_clients.values())
    socks_usernames = sorted(client["username"] for client in socks5_clients.values())

    if http_usernames:
        lines.append("allow " + ",".join(http_usernames))
        lines.append(f"proxy -n -a -p{http_port}")
        lines.append("")

    if socks_usernames:
        lines.append("allow " + ",".join(socks_usernames))
        lines.append(f"socks -p{socks5_port}")
        lines.append("")

    if not http_usernames and not socks_usernames:
        lines.append("deny *")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def sync_3proxy() -> None:
    config_text = build_3proxy_config()

    if THREEPROXY_CONFIG.exists():
        shutil.copy2(THREEPROXY_CONFIG, THREEPROXY_BACKUP)

    THREEPROXY_CONFIG.write_text(config_text, encoding="utf-8")

    result = subprocess.run(
        ["systemctl", "restart", THREEPROXY_SERVICE],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Не удалось перезапустить 3proxy.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

#!/usr/bin/env python3
import asyncio
import base64
import binascii
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ALLOWED_USER_IDS = {
    int(x.strip())
    for x in os.getenv("ALLOWED_USER_IDS", "").split(",")
    if x.strip()
}

SERVER_ADDR_DEFAULT = os.getenv("SERVER_ADDR_DEFAULT", "").strip()
DEFAULT_FAKE_TLS_HOST = os.getenv("DEFAULT_FAKE_TLS_HOST", "ajax.googleapis.com").strip()

IMAGE = "nineseconds/mtg:2"
BASE_DIR = Path("/opt/mtg-manager")
USERS_DIR = BASE_DIR / "users"
CONFIGS_DIR = BASE_DIR / "configs"
CONTAINER_PREFIX = "mtg-proxy-"
INTERNAL_PORT = 3128

USERS_DIR.mkdir(parents=True, exist_ok=True)
CONFIGS_DIR.mkdir(parents=True, exist_ok=True)

HELP_TEXT = """Команды:
/users
/add
/link <user>
/delete <user>
/logs <user>
/ports
/help

Подсказка:
На шагах ввода IP и hostname можно отправить "." для значения по умолчанию.
"""

def run_cmd(args: List[str], check: bool = True):
    return subprocess.run(args, text=True, capture_output=True, check=check)

def slugify(name: str) -> str:
    name = (name or "").strip().lower()
    name = re.sub(r"[^a-z0-9._-]+", "-", name)
    name = re.sub(r"-{2,}", "-", name).strip("-")
    return name

def metadata_file(user: str):
    return USERS_DIR / f"{user}.json"

def config_file(user: str):
    return CONFIGS_DIR / f"{user}.toml"

def container_name(user: str):
    return f"{CONTAINER_PREFIX}{user}"

def hex_to_base64url(hex_str: str):
    return base64.urlsafe_b64encode(binascii.unhexlify(hex_str)).decode().rstrip("=")

def get_public_ip():
    if SERVER_ADDR_DEFAULT:
        return SERVER_ADDR_DEFAULT
    cp = run_cmd(
        ["bash", "-lc", "curl -4 -fsS --max-time 4 https://api.ipify.org || hostname -I | awk '{print $1}'"],
        check=False,
    )
    return cp.stdout.strip()

def get_ports():
    out = run_cmd(["ss", "-ltnH"], check=False).stdout
    ports = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        addr = parts[3].strip("[]")
        if ":" in addr:
            port = addr.rsplit(":", 1)[-1]
            if port.isdigit():
                ports.add(int(port))
    return sorted(ports)

def is_port_busy(port: int) -> bool:
    return port in set(get_ports())

def generate_secret_hex(host):
    cp = run_cmd(["docker", "run", "--rm", IMAGE, "generate-secret", "--hex", host], check=True)
    lines = cp.stdout.strip().splitlines()
    if not lines:
        raise RuntimeError("Не удалось получить secret")
    secret = lines[-1].strip()
    if not re.fullmatch(r"[A-Fa-f0-9]+", secret):
        raise RuntimeError(f"Некорректный secret: {secret}")
    return secret

def write_config(user, secret):
    config_file(user).write_text(
        f'secret = "{secret}"\n'
        f'bind-to = "0.0.0.0:{INTERNAL_PORT}"\n',
        encoding="utf-8",
    )

def create_container(user, port):
    run_cmd(["docker", "rm", "-f", container_name(user)], check=False)
    cp = run_cmd(
        [
            "docker", "run", "-d",
            "--name", container_name(user),
            "--restart", "unless-stopped",
            "-v", f"{config_file(user)}:/config.toml:ro",
            "-p", f"{port}:{INTERNAL_PORT}/tcp",
            IMAGE,
        ],
        check=False,
    )
    if cp.returncode != 0:
        msg = (cp.stderr or cp.stdout or "").strip()
        raise RuntimeError(msg or "Не удалось запустить контейнер")

def delete_user_files(user: str):
    metadata_file(user).unlink(missing_ok=True)
    config_file(user).unlink(missing_ok=True)

def load_user(user: str):
    path = metadata_file(user)
    if not path.exists():
        raise FileNotFoundError(user)
    return json.loads(path.read_text(encoding="utf-8"))

def save_user(data: Dict):
    metadata_file(data["user"]).write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

def get_logs(user: str, tail: int = 50):
    cp = run_cmd(["docker", "logs", "--tail", str(tail), container_name(user)], check=False)
    text = ((cp.stdout or "") + (cp.stderr or "")).strip()
    return text or "Логи пусты."

def allowed(message: Message) -> bool:
    return bool(message.from_user and message.from_user.id in ALLOWED_USER_IDS)

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

class AddState(StatesGroup):
    waiting_name = State()
    waiting_server = State()
    waiting_port = State()
    waiting_hostname = State()

async def deny(message: Message) -> bool:
    if allowed(message):
        return False
    await message.answer("Доступ запрещён.")
    return True

@dp.message(CommandStart())
async def start_cmd(message: Message):
    if await deny(message):
        return
    await message.answer("Бот запущен.\n\n" + HELP_TEXT)

@dp.message(Command("help"))
async def help_cmd(message: Message):
    if await deny(message):
        return
    await message.answer(HELP_TEXT)

@dp.message(Command("ports"))
async def ports_cmd(message: Message):
    if await deny(message):
        return
    ports = get_ports()
    text = ", ".join(map(str, ports)) if ports else "Пусто"
    await message.answer(f"Занятые TCP-порты:\n{text}")

@dp.message(Command("users"))
async def users_cmd(message: Message):
    if await deny(message):
        return
    files = list(USERS_DIR.glob("*.json"))
    if not files:
        await message.answer("Нет пользователей.")
        return

    lines = []
    for f in sorted(files):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            lines.append(f"{data.get('user')} — порт {data.get('port')}")
        except Exception:
            lines.append(f"{f.stem} — ошибка чтения метаданных")
    await message.answer("\n".join(lines))

@dp.message(Command("link"))
async def link_cmd(message: Message):
    if await deny(message):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2:
        await message.answer("Использование: /link <user>")
        return

    user = slugify(parts[1])
    try:
        data = load_user(user)
    except FileNotFoundError:
        await message.answer("Пользователь не найден.")
        return

    await message.answer(
        f"Пользователь: {data['user']}\n"
        f"Порт: {data['port']}\n"
        f"Hostname: {data['hostname']}\n\n"
        f"{data['link']}"
    )

@dp.message(Command("logs"))
async def logs_cmd(message: Message):
    if await deny(message):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2:
        await message.answer("Использование: /logs <user>")
        return

    user = slugify(parts[1])
    if not metadata_file(user).exists():
        await message.answer("Пользователь не найден.")
        return

    logs = get_logs(user)
    if len(logs) > 3800:
        logs = logs[-3800:]
    await message.answer(f"<pre>{logs}</pre>", parse_mode="HTML")

@dp.message(Command("delete"))
async def delete_cmd(message: Message):
    if await deny(message):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) != 2:
        await message.answer("Использование: /delete <user>")
        return

    user = slugify(parts[1])
    if not metadata_file(user).exists():
        await message.answer("Пользователь не найден.")
        return

    run_cmd(["docker", "rm", "-f", container_name(user)], check=False)
    delete_user_files(user)
    await message.answer(f"Пользователь {user} удалён.")

@dp.message(Command("add"))
async def add_cmd(message: Message, state: FSMContext):
    if await deny(message):
        return
    await state.clear()
    await state.set_state(AddState.waiting_name)
    await message.answer("Введите имя пользователя.")

@dp.message(AddState.waiting_name)
async def add_name(message: Message, state: FSMContext):
    if await deny(message):
        return

    user = slugify(message.text or "")
    if not user:
        await message.answer("Некорректное имя. Попробуй ещё раз.")
        return

    if metadata_file(user).exists():
        await message.answer("Такой пользователь уже существует. Введи другое имя.")
        return

    await state.update_data(user=user)
    default_ip = get_public_ip()
    await state.set_state(AddState.waiting_server)
    await message.answer(
        f"Введите IP/домен сервера.\n"
        f"'.' — использовать: {default_ip}"
    )

@dp.message(AddState.waiting_server)
async def add_server(message: Message, state: FSMContext):
    if await deny(message):
        return

    raw = (message.text or "").strip()
    server = get_public_ip() if raw in ["", ".", "skip"] else raw
    if not server:
        await message.answer("Не удалось определить адрес автоматически. Введи его вручную.")
        return

    await state.update_data(server=server)
    ports = get_ports()
    ports_text = ", ".join(map(str, ports)) if ports else "пусто"
    await state.set_state(AddState.waiting_port)
    await message.answer(
        f"Введите внешний порт.\n"
        f"Занятые порты: {ports_text}"
    )

@dp.message(AddState.waiting_port)
async def add_port(message: Message, state: FSMContext):
    if await deny(message):
        return

    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer("Порт должен быть числом.")
        return

    port = int(raw)
    if port < 1 or port > 65535:
        await message.answer("Порт должен быть в диапазоне 1..65535.")
        return

    if is_port_busy(port):
        await message.answer("Этот порт уже занят. Введи другой.")
        return

    await state.update_data(port=port)
    await state.set_state(AddState.waiting_hostname)
    await message.answer(
        f"Введите hostname для FakeTLS.\n"
        f"'.' — использовать: {DEFAULT_FAKE_TLS_HOST}"
    )

@dp.message(AddState.waiting_hostname)
async def add_hostname(message: Message, state: FSMContext):
    if await deny(message):
        return

    data = await state.get_data()
    user = data["user"]
    server = data["server"]
    port = int(data["port"])
    raw = (message.text or "").strip()
    hostname = DEFAULT_FAKE_TLS_HOST if raw in ["", ".", "skip"] else raw

    await message.answer("Создаю пользователя...")

    try:
        secret = generate_secret_hex(hostname)
        write_config(user, secret)
        create_container(user, port)
        secret_b64 = hex_to_base64url(secret)
        link = f"tg://proxy?server={server}&port={port}&secret={secret_b64}"

        save_user({
            "user": user,
            "port": port,
            "hostname": hostname,
            "server": server,
            "secret_hex": secret,
            "secret_b64": secret_b64,
            "link": link,
        })

    except Exception as e:
        run_cmd(["docker", "rm", "-f", container_name(user)], check=False)
        delete_user_files(user)
        await state.clear()
        text = str(e).strip()
        if len(text) > 3000:
            text = text[-3000:]
        await message.answer(f"Ошибка при создании пользователя:\n{text}")
        return

    await state.clear()
    await message.answer(
        f"Готово.\n\n"
        f"Пользователь: {user}\n"
        f"Сервер: {server}\n"
        f"Порт: {port}\n"
        f"Hostname: {hostname}\n\n"
        f"{link}"
    )

async def main():
    if not BOT_TOKEN:
        raise RuntimeError("Не задан BOT_TOKEN")
    if not ALLOWED_USER_IDS:
        raise RuntimeError("Не задан ALLOWED_USER_IDS")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

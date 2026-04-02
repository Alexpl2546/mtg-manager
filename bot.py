import asyncio
import json
import random
import re
import socket
import subprocess
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

TOKEN = Path(".env").read_text(encoding="utf-8").strip()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CLIENTS_FILE = DATA_DIR / "clients.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

INSTALL_SCRIPT = BASE_DIR / "scripts" / "install-mtproto.sh"
DELETE_SCRIPT = BASE_DIR / "scripts" / "delete-mtproto.sh"

DEFAULT_DOMAIN = "ajax.googleapis.com"
DOMAIN_PRESETS = [
    "ajax.googleapis.com",
    "cdn.jsdelivr.net",
    "www.cloudflare.com",
    "fonts.googleapis.com",
]

bot = Bot(token=TOKEN)
dp = Dispatcher()

pending_actions: dict[int, str] = {}


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Новый прокси"), KeyboardButton(text="👥 Клиенты")],
            [KeyboardButton(text="🌐 Домен")],
            [KeyboardButton(text="🗑 Удалить"), KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери действие",
    )


def domain_menu() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=domain, callback_data=f"set_domain:{domain}")]
        for domain in DOMAIN_PRESETS
    ]
    buttons.append([InlineKeyboardButton(text="✏️ Ввести домен вручную", callback_data="change_domain_manual")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def delete_clients_menu() -> InlineKeyboardMarkup:
    clients = load_clients()
    if not clients:
        return InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Клиентов нет", callback_data="noop")]]
        )

    buttons = []
    for name in sorted(clients.keys()):
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"delete_client:{name}")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def delete_confirm_menu(client_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить удаление", callback_data=f"confirm_delete:{client_name}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete")],
        ]
    )


def clients_menu() -> InlineKeyboardMarkup:
    clients = load_clients()
    if not clients:
        return InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Клиентов нет", callback_data="noop")]]
        )

    buttons = []
    for name in sorted(clients.keys()):
        buttons.append([InlineKeyboardButton(text=name, callback_data=f"show_client:{name}")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not CLIENTS_FILE.exists():
        CLIENTS_FILE.write_text("{}", encoding="utf-8")

    if not SETTINGS_FILE.exists():
        SETTINGS_FILE.write_text(
            json.dumps({"domain": DEFAULT_DOMAIN}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def load_clients() -> dict:
    ensure_storage()
    return json.loads(CLIENTS_FILE.read_text(encoding="utf-8"))


def save_clients(data: dict) -> None:
    ensure_storage()
    CLIENTS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_settings() -> dict:
    ensure_storage()
    data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    data.setdefault("domain", DEFAULT_DOMAIN)
    return data


def save_settings(data: dict) -> None:
    ensure_storage()
    SETTINGS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def normalize_name(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"\s+", "_", name)
    return name


def validate_name(name: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9_\-]{2,40}", name))


def validate_domain(domain: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9.-]{3,253}", domain))


def is_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        return s.connect_ex(("127.0.0.1", port)) != 0


def get_random_port() -> int:
    return random.randint(20000, 40000)


def get_free_port(clients: dict) -> int:
    used_ports = {item["port"] for item in clients.values()}
    for _ in range(500):
        port = get_random_port()
        if port not in used_ports and is_port_free(port):
            return port
    raise RuntimeError("Не удалось подобрать свободный порт")


def create_proxy_for_client(client_name: str) -> dict:
    clients = load_clients()
    settings = load_settings()

    if client_name in clients:
        raise RuntimeError(f"Клиент '{client_name}' уже существует")

    port = get_free_port(clients)
    container_name = f"mtg-{client_name}"
    workdir = f"/opt/mtg-clients/{client_name}"
    domain = settings["domain"]

    result = subprocess.run(
        [
            "bash",
            str(INSTALL_SCRIPT),
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
            f"Ошибка создания прокси.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    parsed = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            parsed[key.strip()] = value.strip()

    if parsed.get("STATUS") != "OK" or "TG_URL" not in parsed:
        raise RuntimeError(f"Неожиданный вывод скрипта:\n{result.stdout}")

    clients[client_name] = {
        "name": client_name,
        "container_name": parsed["CONTAINER"],
        "workdir": parsed["WORKDIR"],
        "port": int(parsed["PORT"]),
        "domain": parsed["DOMAIN"],
        "tg_url": parsed["TG_URL"],
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    save_clients(clients)

    return clients[client_name]


def delete_proxy_for_client(client_name: str) -> dict:
    clients = load_clients()

    if client_name not in clients:
        raise RuntimeError(f"Клиент '{client_name}' не найден")

    client = clients[client_name]

    result = subprocess.run(
        [
            "bash",
            str(DELETE_SCRIPT),
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
            f"Ошибка удаления прокси.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )

    del clients[client_name]
    save_clients(clients)

    return client


async def send_help(message: Message):
    await message.answer(
        "Бот управления MTProto.\n\n"
        "Кнопки:\n"
        "➕ Новый прокси — создать клиента\n"
        "👥 Клиенты — список клиентов\n"
        "🌐 Домен — текущий домен и смена домена\n"
        "🗑 Удалить — удалить клиента\n"
        "❓ Помощь — справка\n\n"
        "Команды:\n"
        "/newproxy\n"
        "/list\n"
        "/domain\n"
        "/setdomain <домен>\n"
        "/show <имя>\n"
        "/delete <имя>",
        reply_markup=main_menu(),
    )


async def send_clients_list(message: Message):
    clients = load_clients()

    if not clients:
        await message.answer("Список клиентов пуст.", reply_markup=main_menu())
        return

    await message.answer(
        "Выбери клиента:",
        reply_markup=main_menu(),
    )
    await message.answer(
        "Список клиентов:",
        reply_markup=clients_menu(),
    )


async def send_ports_list(message: Message):
    clients = load_clients()

    if not clients:
        await message.answer("Занятых портов нет.", reply_markup=main_menu())
        return

    ports = sorted({data["port"] for data in clients.values()})
    text = "Занятые порты:\n" + "\n".join(str(port) for port in ports)
    await message.answer(text, reply_markup=main_menu())


async def send_domain_info(message: Message):
    settings = load_settings()
    await message.answer(
        f"Текущий домен для новых прокси:\n{settings['domain']}",
        reply_markup=main_menu(),
    )
    await message.answer(
        "Выбери домен кнопкой ниже или введи свой вручную.",
        reply_markup=domain_menu(),
    )


async def show_client_info(message: Message, client_name: str):
    clients = load_clients()

    if client_name not in clients:
        await message.answer("Клиент не найден.", reply_markup=main_menu())
        return

    client = clients[client_name]
    await message.answer(
        f"Имя пользователя: {client['name']}\n"
        f"Порт: {client['port']}\n"
        f"Домен: {client['domain']}\n"
        f"Ссылка: {client['tg_url']}",
        reply_markup=main_menu(),
    )


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await send_help(message)


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await send_help(message)


@dp.message(Command("list"))
async def cmd_list(message: Message):
    await send_clients_list(message)


@dp.message(Command("ports"))
async def cmd_ports(message: Message):
    await send_ports_list(message)


@dp.message(Command("domain"))
async def cmd_domain(message: Message):
    await send_domain_info(message)


@dp.message(Command("setdomain"))
async def cmd_setdomain(message: Message):
    parts = message.text.split(maxsplit=1)

    if len(parts) != 2:
        await message.answer("Использование: /setdomain <домен>", reply_markup=main_menu())
        return

    domain = parts[1].strip().lower()

    if not validate_domain(domain):
        await message.answer("Некорректный домен.", reply_markup=main_menu())
        return

    settings = load_settings()
    settings["domain"] = domain
    save_settings(settings)

    await message.answer(
        f"Домен для новых прокси обновлён:\n{domain}\n\n"
        "Уже созданные прокси не изменяются.",
        reply_markup=main_menu(),
    )


@dp.message(Command("newproxy"))
async def cmd_newproxy(message: Message):
    pending_actions[message.from_user.id] = "waiting_client_name"
    await message.answer(
        "Введи имя нового клиента.\n"
        "Оно будет сохранено в нижнем регистре.\n"
        "Допустимы латинские буквы (a-z), цифры, дефис и подчёркивание.",
        reply_markup=main_menu(),
    )


@dp.message(Command("show"))
async def cmd_show(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        await message.answer("Использование: /show <имя>", reply_markup=main_menu())
        return

    client_name = normalize_name(parts[1])
    await show_client_info(message, client_name)


@dp.message(Command("delete"))
async def cmd_delete(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) == 2:
        client_name = normalize_name(parts[1])
        clients = load_clients()

        if client_name not in clients:
            await message.answer("Клиент не найден.", reply_markup=main_menu())
            return

        await message.answer(
            f"Ты точно хочешь удалить клиента '{client_name}'?",
            reply_markup=main_menu(),
        )
        await message.answer(
            "Подтверди удаление:",
            reply_markup=delete_confirm_menu(client_name),
        )
        return

    await message.answer(
        "Выбери клиента для удаления:",
        reply_markup=main_menu(),
    )
    await message.answer(
        "Список клиентов:",
        reply_markup=delete_clients_menu(),
    )


@dp.message(F.text == "➕ Новый прокси")
async def btn_newproxy(message: Message):
    pending_actions[message.from_user.id] = "waiting_client_name"
    await message.answer(
        "Введи имя нового клиента.\n"
        "Оно будет сохранено в нижнем регистре.\n"
        "Допустимы латинские буквы (a-z), цифры, дефис и подчёркивание.",
        reply_markup=main_menu(),
    )


@dp.message(F.text == "👥 Клиенты")
async def btn_clients(message: Message):
    await send_clients_list(message)


@dp.message(F.text == "🌐 Домен")
async def btn_domain(message: Message):
    await send_domain_info(message)


@dp.message(F.text == "🗑 Удалить")
async def btn_delete(message: Message):
    await message.answer(
        "Выбери клиента для удаления:",
        reply_markup=main_menu(),
    )
    await message.answer(
        "Список клиентов:",
        reply_markup=delete_clients_menu(),
    )


@dp.message(F.text == "❓ Помощь")
async def btn_help(message: Message):
    await send_help(message)


@dp.callback_query(F.data == "noop")
async def callback_noop(callback: CallbackQuery):
    await callback.answer()


@dp.callback_query(F.data == "cancel_delete")
async def callback_cancel_delete(callback: CallbackQuery):
    await callback.message.answer(
        "Удаление отменено.",
        reply_markup=main_menu(),
    )
    await callback.answer("Отменено")


@dp.callback_query(F.data == "change_domain_manual")
async def callback_change_domain_manual(callback: CallbackQuery):
    pending_actions[callback.from_user.id] = "waiting_domain"
    await callback.message.answer(
        "Введи новый домен для генерации секретов.\n"
        "Например: ajax.googleapis.com",
        reply_markup=main_menu(),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("set_domain:"))
async def callback_set_domain(callback: CallbackQuery):
    domain = callback.data.split(":", 1)[1].strip().lower()

    if not validate_domain(domain):
        await callback.message.answer("Некорректный домен.", reply_markup=main_menu())
        await callback.answer()
        return

    settings = load_settings()
    settings["domain"] = domain
    save_settings(settings)

    await callback.message.answer(
        f"Домен для новых прокси обновлён:\n{domain}\n\n"
        "Уже созданные прокси не изменяются.",
        reply_markup=main_menu(),
    )
    await callback.answer("Домен обновлён")


@dp.callback_query(F.data.startswith("delete_client:"))
async def callback_delete_client(callback: CallbackQuery):
    client_name = callback.data.split(":", 1)[1]
    clients = load_clients()

    if client_name not in clients:
        await callback.message.answer("Клиент не найден.", reply_markup=main_menu())
        await callback.answer()
        return

    await callback.message.answer(
        f"Ты точно хочешь удалить клиента '{client_name}'?",
        reply_markup=main_menu(),
    )
    await callback.message.answer(
        "Подтверди удаление:",
        reply_markup=delete_confirm_menu(client_name),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("confirm_delete:"))
async def callback_confirm_delete(callback: CallbackQuery):
    client_name = callback.data.split(":", 1)[1]

    try:
        client = await asyncio.to_thread(delete_proxy_for_client, client_name)
    except Exception as e:
        await callback.message.answer(f"Ошибка удаления:\n{e}", reply_markup=main_menu())
        await callback.answer()
        return

    await callback.message.answer(
        f"Клиент '{client['name']}' удалён.\n"
        f"Контейнер {client['container_name']} остановлен и удалён.\n"
        f"Папка {client['workdir']} удалена.",
        reply_markup=main_menu(),
    )
    await callback.answer("Клиент удалён")


@dp.callback_query(F.data.startswith("show_client:"))
async def callback_show_client(callback: CallbackQuery):
    client_name = callback.data.split(":", 1)[1]
    clients = load_clients()

    if client_name not in clients:
        await callback.message.answer("Клиент не найден.", reply_markup=main_menu())
        await callback.answer()
        return

    client = clients[client_name]
    await callback.message.answer(
        f"Имя пользователя: {client['name']}\n"
        f"Порт: {client['port']}\n"
        f"Домен: {client['domain']}\n"
        f"Ссылка: {client['tg_url']}",
        reply_markup=main_menu(),
    )
    await callback.answer()


@dp.message(F.text)
async def handle_text(message: Message):
    user_id = message.from_user.id
    action = pending_actions.get(user_id)

    if action == "waiting_client_name":
        raw_name = message.text.strip()
        client_name = normalize_name(raw_name)

        if not validate_name(client_name):
            await message.answer(
                "Некорректное имя.\n"
                "Используй 2–40 символов: латинские буквы (a-z), цифры, дефис, подчёркивание.\n"
                "Имя будет приведено к нижнему регистру (только a-z).",
                reply_markup=main_menu(),
            )
            return

        pending_actions.pop(user_id, None)

        await message.answer(
            f"Создаю прокси для клиента '{client_name}'...",
            reply_markup=main_menu(),
        )

        try:
            client = await asyncio.to_thread(create_proxy_for_client, client_name)
        except Exception as e:
            await message.answer(f"Ошибка:\n{e}", reply_markup=main_menu())
            return

        await message.answer(
            f"Имя пользователя: {client['name']}\n"
            f"Порт: {client['port']}\n"
            f"Домен: {client['domain']}\n"
            f"Ссылка: {client['tg_url']}",
            reply_markup=main_menu(),
        )
        return

    if action == "waiting_domain":
        domain = message.text.strip().lower()

        if not validate_domain(domain):
            await message.answer("Некорректный домен.", reply_markup=main_menu())
            return

        pending_actions.pop(user_id, None)
        settings = load_settings()
        settings["domain"] = domain
        save_settings(settings)

        await message.answer(
            f"Домен для новых прокси обновлён:\n{domain}\n\n"
            "Уже созданные прокси не изменяются.",
            reply_markup=main_menu(),
        )
        return


async def main():
    ensure_storage()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from config import load_settings as load_app_settings
from providers.http_manager import HTTPProvider
from providers.socks5_manager import SOCKS5Provider
from providers.telemt_manager import TelemtProvider
from utils.auth import AdminOnlyMiddleware
from utils.keyboards import (
    action_keyboard,
    delete_confirm_keyboard,
    names_inline_keyboard,
    protocol_keyboard,
)
from utils.state import (
    get_action,
    get_protocol,
    reset_action,
    set_action,
    set_protocol,
)
from utils.validation import normalize_client_name, validate_client_name

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dp = Dispatcher()

PROVIDERS = {
    "Telemt": TelemtProvider(),
    "HTTP": HTTPProvider(),
    "SOCKS5": SOCKS5Provider(),
}


# =========================
# START
# =========================
@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "Выбери протокол:",
        reply_markup=protocol_keyboard()
    )


# =========================
# ВЫБОР ПРОТОКОЛА
# =========================
@dp.message(lambda m: m.text in PROVIDERS.keys())
async def choose_protocol(message: Message):
    protocol = message.text
    set_protocol(message.from_user.id, protocol)

    await message.answer(
        f"Выбран протокол: {protocol}",
        reply_markup=action_keyboard(protocol)
    )


# =========================
# СМЕНА ПРОТОКОЛА
# =========================
@dp.message(lambda m: m.text == "⬅️ Сменить протокол")
async def change_protocol(message: Message):
    set_protocol(message.from_user.id, None)
    reset_action(message.from_user.id)
    await message.answer(
        "Выбери протокол:",
        reply_markup=protocol_keyboard()
    )

# =========================
# СОЗДАНИЕ КЛИЕНТА
# =========================
@dp.message(lambda m: m.text == "➕ Новый прокси")
async def create_proxy(message: Message):
    protocol = get_protocol(message.from_user.id)

    if not protocol:
        await message.answer("Сначала выбери протокол")
        return

    set_action(message.from_user.id, "create")

    await message.answer("Введи имя клиента:")

@dp.message(lambda m: get_action(m.from_user.id) == "create")
async def handle_create(message: Message):
    name = normalize_client_name(message.text)
    protocol = get_protocol(message.from_user.id)

    if not protocol:
        reset_action(message.from_user.id)
        await message.answer("Сначала выбери протокол", reply_markup=protocol_keyboard())
        return

    if not validate_client_name(name):
        await message.answer(
            "Некорректное имя. Используй 2–40 символов: a-z, 0-9, дефис или подчёркивание."
        )
        return

    provider = PROVIDERS[protocol]

    try:
        client = await asyncio.to_thread(provider.create_client, name)
    except ValueError as exc:
        reset_action(message.from_user.id)
        await message.answer(f"Ошибка: {exc}", reply_markup=action_keyboard(protocol))
        return
    except Exception:
        logger.exception("Failed to create %s client %s", protocol, name)
        reset_action(message.from_user.id)
        await message.answer(
            "Не удалось создать клиента. Подробности записаны в журнал сервиса.",
            reply_markup=action_keyboard(protocol),
        )
        return

    reset_action(message.from_user.id)

    if protocol == "Telemt":
        tg_url = client.get("tg_url") or "Ссылка пока не получена"
        text = (
            f"Имя: {name}\n"
            f"Порт: {client.get('port')}\n"
            f"Домен: {client.get('domain')}\n"
            f"Ссылка: {tg_url}"
        )
    else:
        host = client.get("host")
        port = client.get("port")
        username = client.get("username")
        password = client.get("password")

        text = (
            f"Имя: {name}\n"
            f"Логин: {username}\n"
            f"Пароль: {password}\n"
            f"Адрес: {host}:{port}"
        )

    if protocol == "SOCKS5":
        tg_link = f"tg://socks?server={host}&port={port}&user={username}&pass={password}"
        text += f"\nСсылка: {tg_link}"

    await message.answer(text, reply_markup=action_keyboard(protocol))

# =========================
# СПИСОК КЛИЕНТОВ
# =========================
@dp.message(lambda m: m.text == "👥 Клиенты")
async def list_clients(message: Message):
    protocol = get_protocol(message.from_user.id)

    if not protocol:
        await message.answer("Сначала выбери протокол")
        return

    provider = PROVIDERS[protocol]
    clients = provider.list_clients()

    await message.answer(
        "Выбери клиента:",
        reply_markup=names_inline_keyboard(list(clients.keys()), "show")
    )


# =========================
# ПОКАЗ КЛИЕНТА
# =========================
@dp.callback_query(lambda c: c.data.startswith("show:"))
async def show_client(callback: CallbackQuery):
    name = callback.data.split(":", 1)[1]
    protocol = get_protocol(callback.from_user.id)
    if not protocol:
        await callback.message.answer("Сначала выбери протокол", reply_markup=protocol_keyboard())
        await callback.answer()
        return

    provider = PROVIDERS[protocol]

    client = provider.get_client(name)

    if not client:
        await callback.answer("Не найден")
        return

    if protocol == "Telemt":
        tg_url = client.get("tg_url") or "Ссылка пока не получена"
        text = (
            f"Имя: {name}\n"
            f"Порт: {client.get('port')}\n"
            f"Домен: {client.get('domain')}\n"
            f"Ссылка: {tg_url}"
        )
    else:
        host = client.get("host")
        port = client.get("port")
        username = client.get("username")
        password = client.get("password")

        text = (
            f"Имя: {name}\n"
            f"Логин: {username}\n"
            f"Пароль: {password}\n"
            f"Адрес: {host}:{port}"
        )

    if protocol == "SOCKS5":
        tg_link = f"tg://socks?server={host}&port={port}&user={username}&pass={password}"
        text += f"\nСсылка: {tg_link}"

    await callback.message.answer(text)
    await callback.answer()


# =========================
# УДАЛЕНИЕ
# =========================
@dp.message(lambda m: m.text == "🗑 Удалить")
async def delete_client(message: Message):
    protocol = get_protocol(message.from_user.id)

    if not protocol:
        await message.answer("Сначала выбери протокол")
        return

    provider = PROVIDERS[protocol]
    clients = provider.list_clients()

    await message.answer(
        "Выбери клиента для удаления:",
        reply_markup=names_inline_keyboard(list(clients.keys()), "delete")
    )


@dp.callback_query(lambda c: c.data.startswith("delete:"))
async def confirm_delete(callback: CallbackQuery):
    name = callback.data.split(":", 1)[1]

    await callback.message.answer(
        f"Удалить {name}?",
        reply_markup=delete_confirm_keyboard(name)
    )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("confirm_delete:"))
async def delete_confirmed(callback: CallbackQuery):
    name = callback.data.split(":", 1)[1]
    protocol = get_protocol(callback.from_user.id)
    if not protocol:
        await callback.message.answer("Сначала выбери протокол", reply_markup=protocol_keyboard())
        await callback.answer()
        return

    provider = PROVIDERS[protocol]

    try:
        await asyncio.to_thread(provider.delete_client, name)
        await callback.message.answer(f"{name} удалён")
    except ValueError as exc:
        await callback.message.answer(f"Ошибка: {exc}")
    except Exception:
        logger.exception("Failed to delete %s client %s", protocol, name)
        await callback.message.answer(
            "Не удалось удалить клиента. Подробности записаны в журнал сервиса."
        )

    await callback.answer()


@dp.callback_query(lambda c: c.data == "cancel_delete")
async def cancel_delete(callback: CallbackQuery):
    await callback.message.answer("Удаление отменено")
    await callback.answer()


@dp.callback_query(lambda c: c.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()


# =========================
# ПОМОЩЬ
# =========================
@dp.message(lambda m: m.text == "❓ Помощь")
async def help_handler(message: Message):
    protocol = get_protocol(message.from_user.id)

    if not protocol:
        await message.answer(
            "Сначала выбери протокол.",
            reply_markup=protocol_keyboard()
        )
        return

    if protocol == "Telemt":
        text = (
            "Текущий протокол: Telemt\n\n"
            "Доступные действия:\n"
            "➕ Новый прокси — создать клиента через Telemt Control API\n"
            "👥 Клиенты — показать список клиентов\n"
            "🗑 Удалить — удалить клиента\n"
            "⬅️ Сменить протокол — вернуться к выбору протокола\n\n"
            "Домен Telemt меняется только отдельной миграцией, "
            "иначе старые ссылки перестанут работать."
        )
    else:
        text = (
            f"Текущий протокол: {protocol}\n\n"
            "Доступные действия:\n"
            "➕ Новый прокси — создать клиента\n"
            "👥 Клиенты — показать список клиентов\n"
            "🗑 Удалить — удалить клиента\n"
            "⬅️ Сменить протокол — вернуться к выбору протокола"
        )

    await message.answer(text, reply_markup=action_keyboard(protocol))


# =========================
# ЗАПУСК
# =========================
async def main():
    settings = load_app_settings()
    admin_middleware = AdminOnlyMiddleware(settings.admin_ids)
    dp.message.outer_middleware(admin_middleware)
    dp.callback_query.outer_middleware(admin_middleware)

    bot = Bot(token=settings.bot_token)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

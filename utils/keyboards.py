from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

PROTOCOL_LABELS = {
    "telemt": "Telemt",
    "http": "HTTP",
    "socks5": "SOCKS5",
}


def protocol_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Telemt")],
            [KeyboardButton(text="HTTP"), KeyboardButton(text="SOCKS5")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери протокол",
    )


def action_keyboard(protocol: str | None) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="➕ Новый прокси"), KeyboardButton(text="👥 Клиенты")],
    ]

    rows.append([KeyboardButton(text="🗑 Удалить"), KeyboardButton(text="❓ Помощь")])
    rows.append([KeyboardButton(text="⬅️ Сменить протокол")])

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder="Выбери действие",
    )


def names_inline_keyboard(
    names: list[str],
    prefix: str,
    empty_text: str = "Список пуст",
) -> InlineKeyboardMarkup:
    if not names:
        return InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=empty_text, callback_data="noop")]]
        )

    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"{prefix}:{name}")]
        for name in sorted(names)
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def delete_confirm_keyboard(name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить удаление",
                    callback_data=f"confirm_delete:{name}",
                )
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete")],
        ]
    )

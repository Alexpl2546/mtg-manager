import os
from dataclasses import dataclass


def _parse_admin_ids(raw_value: str) -> frozenset[int]:
    values = {item.strip() for item in raw_value.split(",") if item.strip()}
    try:
        return frozenset(int(item) for item in values)
    except ValueError as exc:
        raise RuntimeError("ADMIN_IDS must contain comma-separated Telegram user IDs") from exc


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: frozenset[int]


def load_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    admin_ids = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))

    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not configured")
    if not admin_ids:
        raise RuntimeError("ADMIN_IDS is not configured")

    return Settings(bot_token=bot_token, admin_ids=admin_ids)

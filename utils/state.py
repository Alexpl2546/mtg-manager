from typing import Any

USER_STATE: dict[int, dict[str, Any]] = {}


def ensure_user(user_id: int) -> None:
    if user_id not in USER_STATE:
        USER_STATE[user_id] = {
            "protocol": None,
            "action": None,
        }


def set_protocol(user_id: int, protocol: str) -> None:
    ensure_user(user_id)
    USER_STATE[user_id]["protocol"] = protocol


def get_protocol(user_id: int) -> str | None:
    ensure_user(user_id)
    return USER_STATE[user_id].get("protocol")


def set_action(user_id: int, action: str | None) -> None:
    ensure_user(user_id)
    USER_STATE[user_id]["action"] = action


def get_action(user_id: int) -> str | None:
    ensure_user(user_id)
    return USER_STATE[user_id].get("action")


def reset_action(user_id: int) -> None:
    ensure_user(user_id)
    USER_STATE[user_id]["action"] = None

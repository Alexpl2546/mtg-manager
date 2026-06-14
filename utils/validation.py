import re

CLIENT_NAME_PATTERN = re.compile(r"[a-z0-9_-]{2,40}")


def normalize_client_name(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def validate_client_name(value: str) -> bool:
    return CLIENT_NAME_PATTERN.fullmatch(value) is not None

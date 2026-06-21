from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum


class Role(StrEnum):
    USER = "user"
    ADMIN = "admin"


class Protocol(StrEnum):
    VLESS = "vless"
    AMNEZIAWG = "amneziawg"


class ConfigStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


@dataclass(frozen=True)
class User:
    id: str
    name: str
    telegram: str
    role: Role = Role.USER
    email: str | None = None
    subscription_until: str = field(
        default_factory=lambda: (datetime.now(UTC) + timedelta(days=92)).date().isoformat()
    )
    max_devices: int = 5


@dataclass(frozen=True)
class Server:
    id: str
    name: str
    location: str
    protocols: tuple[Protocol, ...]
    host: str
    is_active: bool = True


@dataclass(frozen=True)
class Device:
    id: str
    user_id: str
    name: str
    device_type: str
    created_at: str


@dataclass(frozen=True)
class Config:
    id: str
    user_id: str
    device_id: str
    server_id: str
    protocol: Protocol
    status: ConfigStatus
    display_name: str
    created_at: str
    revoked_at: str | None
    uri: str
    config_text: str


@dataclass(frozen=True)
class IssuedConfig:
    device: Device
    config: Config

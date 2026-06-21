from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from vpn_service.models import Config, ConfigStatus, Device, IssuedConfig, Protocol, Server, User
from vpn_service.providers.amneziawg import AmneziaWgProvider
from vpn_service.providers.vless import VlessProvider
from vpn_service.storage import JsonRepository


class ConfigService:
    def __init__(self, repository: JsonRepository | None = None) -> None:
        self.repository = repository or JsonRepository()
        self.providers = {
            Protocol.VLESS: VlessProvider(),
            Protocol.AMNEZIAWG: AmneziaWgProvider(),
        }

    def get_current_user(self, user_id: str = "demo-user") -> User:
        state = self.repository.state()
        raw = state["users"].get(user_id) or state["users"]["demo-user"]
        return User(**raw)

    def get_subscription(self, user_id: str = "demo-user") -> dict[str, Any]:
        user = self.get_current_user(user_id)
        configs = [
            item for item in self.list_configs(user.id) if item.status == ConfigStatus.ACTIVE
        ]
        return {
            "plan": "Premium",
            "status": "active",
            "expiresAt": user.subscription_until,
            "maxConnections": user.max_devices,
            "activeConnections": len(configs),
        }

    def list_servers(self) -> list[Server]:
        state = self.repository.state()
        return [Server(**item) for item in state["servers"].values() if item.get("is_active", True)]

    def list_configs(self, user_id: str = "demo-user") -> list[Config]:
        state = self.repository.state()
        return [
            Config(**item)
            for item in state["configs"].values()
            if item["user_id"] == user_id
        ]

    def get_config(self, config_id: str, user_id: str = "demo-user") -> Config:
        state = self.repository.state()
        raw = state["configs"].get(config_id)
        if not raw or raw["user_id"] != user_id:
            raise ValueError("Configuration not found")
        return Config(**raw)

    def create_config(
        self,
        *,
        user_id: str = "demo-user",
        device_name: str,
        device_type: str,
        protocol: Protocol,
        server_id: str | None = None,
    ) -> IssuedConfig:
        state = self.repository.state()
        user = self.get_current_user(user_id)
        active_count = len(
            [item for item in self.list_configs(user.id) if item.status == ConfigStatus.ACTIVE]
        )
        if active_count >= user.max_devices:
            raise ValueError("Device limit reached")

        server = self._select_server(state, protocol, server_id)
        config_id = f"cfg_{uuid.uuid4().hex[:12]}"
        device = Device(
            id=f"dev_{uuid.uuid4().hex[:12]}",
            user_id=user.id,
            name=device_name,
            device_type=device_type,
            created_at=datetime.now(UTC).isoformat(),
        )
        issued = self.providers[protocol].issue(
            config_id=config_id,
            device_name=device_name,
            server=server,
        )
        config = Config(
            id=config_id,
            user_id=user.id,
            device_id=device.id,
            server_id=server.id,
            protocol=protocol,
            status=ConfigStatus.ACTIVE,
            display_name=device_name,
            created_at=device.created_at,
            revoked_at=None,
            uri=issued["uri"],
            config_text=issued["config_text"],
        )

        state["devices"][device.id] = asdict(device)
        state["configs"][config.id] = asdict(config)
        self.repository.save(state)
        return IssuedConfig(device=device, config=config)

    def revoke_config(self, config_id: str, user_id: str = "demo-user") -> Config:
        state = self.repository.state()
        raw = state["configs"].get(config_id)
        if not raw or raw["user_id"] != user_id:
            raise ValueError("Configuration not found")
        if raw["status"] == ConfigStatus.REVOKED:
            return Config(**raw)

        server = Server(**state["servers"][raw["server_id"]])
        protocol = Protocol(raw["protocol"])
        self.providers[protocol].revoke(config_id=config_id, server=server)

        raw["status"] = ConfigStatus.REVOKED
        raw["revoked_at"] = datetime.now(UTC).isoformat()
        state["configs"][config_id] = raw
        self.repository.save(state)
        return Config(**raw)

    def _select_server(
        self,
        state: dict[str, Any],
        protocol: Protocol,
        server_id: str | None,
    ) -> Server:
        servers = [Server(**item) for item in state["servers"].values()]
        if server_id:
            for server in servers:
                if server.id == server_id and protocol in server.protocols and server.is_active:
                    return server
            raise ValueError("Server not available for selected protocol")

        for server in servers:
            if server.is_active and protocol in server.protocols:
                return server

        raise ValueError("No active server for selected protocol")

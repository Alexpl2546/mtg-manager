from __future__ import annotations

import base64
import os
import secrets

from vpn_service.models import Server
from vpn_service.providers.base import ProviderResult, VpnProvider
from vpn_service.providers.node_agent import MockNodeAgent


def _mock_key() -> str:
    return base64.b64encode(secrets.token_bytes(32)).decode("ascii")


class AmneziaWgProvider(VpnProvider):
    def __init__(self, node_agent: MockNodeAgent | None = None) -> None:
        self.node_agent = node_agent or MockNodeAgent()

    def issue(self, *, config_id: str, device_name: str, server: Server) -> ProviderResult:
        private_key = _mock_key()
        public_key = _mock_key()
        server_public_key = os.getenv("AMNEZIAWG_SERVER_PUBLIC_KEY", "replace-with-real-server-key")
        endpoint = os.getenv("AMNEZIAWG_ENDPOINT", f"{server.host}:51820")
        allowed_ips = os.getenv("AMNEZIAWG_ALLOWED_IPS", "0.0.0.0/0, ::/0")
        dns = os.getenv("AMNEZIAWG_DNS", "1.1.1.1")
        keepalive = os.getenv("AMNEZIAWG_KEEPALIVE", "25")
        address = os.getenv("AMNEZIAWG_CLIENT_ADDRESS", "10.8.0.2/32")

        config_text = "\n".join(
            [
                "[Interface]",
                f"# Device = {device_name}",
                f"PrivateKey = {private_key}",
                f"Address = {address}",
                f"DNS = {dns}",
                "",
                "[Peer]",
                f"PublicKey = {server_public_key}",
                f"Endpoint = {endpoint}",
                f"AllowedIPs = {allowed_ips}",
                f"PersistentKeepalive = {keepalive}",
                "",
                "# AmneziaWG 2.0 parameters are reserved for the real node agent.",
            ]
        )
        self.node_agent.create_amneziawg_client(config_id=config_id, server=server)

        return ProviderResult(
            uri=config_text,
            config_text=config_text,
            clientPublicKey=public_key,
            serverPublicKey=server_public_key,
            endpoint=endpoint,
            allowedIps=allowed_ips,
            dns=dns,
            keepalive=keepalive,
        )

    def revoke(self, *, config_id: str, server: Server) -> None:
        self.node_agent.revoke_client(config_id=config_id, server=server)

from __future__ import annotations

import os
import uuid
from urllib.parse import quote, urlencode

from vpn_service.models import Server
from vpn_service.providers.base import ProviderResult, VpnProvider
from vpn_service.providers.node_agent import MockNodeAgent


class VlessProvider(VpnProvider):
    def __init__(self, node_agent: MockNodeAgent | None = None) -> None:
        self.node_agent = node_agent or MockNodeAgent()

    def issue(self, *, config_id: str, device_name: str, server: Server) -> ProviderResult:
        client_uuid = str(uuid.uuid4())
        host = os.getenv("VLESS_HOST", server.host)
        port = os.getenv("VLESS_PORT", "443")
        server_name = os.getenv("VLESS_SERVER_NAME", host)
        public_key = os.getenv("VLESS_PUBLIC_KEY", "replace-with-real-public-key")
        short_id = os.getenv("VLESS_SHORT_ID", "abcd1234")
        fingerprint = os.getenv("VLESS_FINGERPRINT", "chrome")
        flow = os.getenv("VLESS_FLOW", "xtls-rprx-vision")
        network = os.getenv("VLESS_NETWORK", "tcp")
        security = os.getenv("VLESS_SECURITY", "reality")

        query = urlencode(
            {
                "type": network,
                "security": security,
                "pbk": public_key,
                "fp": fingerprint,
                "sni": server_name,
                "sid": short_id,
                "flow": flow,
            }
        )
        uri = f"vless://{client_uuid}@{host}:{port}?{query}#{quote(device_name)}"
        self.node_agent.create_vless_client(config_id=config_id, server=server)

        return ProviderResult(
            uri=uri,
            config_text=uri,
            uuid=client_uuid,
            host=host,
            port=port,
            serverName=server_name,
            publicKey=public_key,
            shortId=short_id,
            fingerprint=fingerprint,
            flow=flow,
            network=network,
            security=security,
        )

    def revoke(self, *, config_id: str, server: Server) -> None:
        self.node_agent.revoke_client(config_id=config_id, server=server)

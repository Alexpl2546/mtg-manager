from __future__ import annotations

from vpn_service.models import Server


class MockNodeAgent:
    """Placeholder for future Xray and AmneziaWG node control."""

    def create_vless_client(self, *, config_id: str, server: Server) -> None:
        _ = (config_id, server)

    def create_amneziawg_client(self, *, config_id: str, server: Server) -> None:
        _ = (config_id, server)

    def revoke_client(self, *, config_id: str, server: Server) -> None:
        _ = (config_id, server)

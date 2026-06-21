from __future__ import annotations

from abc import ABC, abstractmethod

from vpn_service.models import Server


class ProviderResult(dict):
    uri: str
    config_text: str


class VpnProvider(ABC):
    @abstractmethod
    def issue(self, *, config_id: str, device_name: str, server: Server) -> ProviderResult:
        raise NotImplementedError

    @abstractmethod
    def revoke(self, *, config_id: str, server: Server) -> None:
        raise NotImplementedError

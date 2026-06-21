import pytest

from vpn_service.models import ConfigStatus, Protocol
from vpn_service.service import ConfigService
from vpn_service.storage import JsonRepository


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.setenv("VPN_SERVICE_DATA_PATH", str(tmp_path / "vpn_service.json"))
    monkeypatch.setenv("VLESS_PUBLIC_KEY", "public-key")
    monkeypatch.setenv("AMNEZIAWG_SERVER_PUBLIC_KEY", "server-key")
    return ConfigService(JsonRepository())


def test_create_vless_config(service):
    issued = service.create_config(
        device_name="iPhone",
        device_type="phone",
        protocol=Protocol.VLESS,
    )

    assert issued.config.protocol == Protocol.VLESS
    assert issued.config.status == ConfigStatus.ACTIVE
    assert issued.config.uri.startswith("vless://")
    assert "security=reality" in issued.config.uri
    assert "public-key" in issued.config.uri


def test_create_amneziawg_config(service):
    issued = service.create_config(
        device_name="Router",
        device_type="router",
        protocol=Protocol.AMNEZIAWG,
    )

    assert issued.config.protocol == Protocol.AMNEZIAWG
    assert "[Interface]" in issued.config.config_text
    assert "[Peer]" in issued.config.config_text
    assert "server-key" in issued.config.config_text


def test_revoke_config(service):
    issued = service.create_config(
        device_name="Laptop",
        device_type="computer",
        protocol=Protocol.VLESS,
    )

    revoked = service.revoke_config(issued.config.id)

    assert revoked.status == ConfigStatus.REVOKED
    assert revoked.revoked_at


def test_device_limit_is_enforced(service):
    for index in range(5):
        service.create_config(
            device_name=f"device-{index}",
            device_type="phone",
            protocol=Protocol.VLESS,
        )

    with pytest.raises(ValueError, match="Device limit"):
        service.create_config(
            device_name="extra",
            device_type="phone",
            protocol=Protocol.VLESS,
        )

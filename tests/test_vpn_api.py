from fastapi.testclient import TestClient

from vpn_service.api import app


def test_api_config_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setenv("VPN_SERVICE_DATA_PATH", str(tmp_path / "vpn_service.json"))
    client = TestClient(app)

    response = client.post(
        "/configs",
        json={
            "deviceName": "iPhone",
            "deviceType": "Телефон",
            "protocol": "vless",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["protocol"] == "VLESS Reality"

    config_id = payload["id"]
    assert client.get(f"/configs/{config_id}/qr").json()["value"].startswith("vless://")
    assert client.get(f"/configs/{config_id}/download").status_code == 200

    revoked = client.post(f"/configs/{config_id}/revoke")

    assert revoked.status_code == 200
    assert revoked.json()["status"] == "Отключено"


def test_api_servers(tmp_path, monkeypatch):
    monkeypatch.setenv("VPN_SERVICE_DATA_PATH", str(tmp_path / "vpn_service.json"))
    client = TestClient(app)

    response = client.get("/servers")

    assert response.status_code == 200
    assert response.json()[0]["protocols"] == ["vless", "amneziawg"]

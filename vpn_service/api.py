from __future__ import annotations

import os
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from pydantic import BaseModel, Field

from vpn_service.models import Config, Protocol
from vpn_service.service import ConfigService

app = FastAPI(title="VPN Config Service", version="0.1.0")


class LoginRequest(BaseModel):
    telegram: str
    password: str


class CreateConfigRequest(BaseModel):
    deviceName: str = Field(min_length=2, max_length=64)
    deviceType: str = Field(min_length=2, max_length=32)
    protocol: Literal["vless", "amneziawg", "auto"] = "auto"
    serverId: str | None = None


def get_service() -> ConfigService:
    return ConfigService()


def current_user_id(authorization: str | None = Header(default=None)) -> str:
    expected_token = os.getenv("VPN_API_TOKEN", "").strip()
    if expected_token and authorization != f"Bearer {expected_token}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    return "demo-user"


def serialize_config(config: Config, service: ConfigService | None = None) -> dict:
    device_type = "Компьютер"
    if service is not None:
        device = service.repository.state()["devices"].get(config.device_id)
        if device:
            device_type = device.get("device_type") or device_type

    return {
        "id": config.id,
        "deviceName": config.display_name,
        "deviceType": device_type,
        "protocol": "VLESS Reality" if config.protocol == Protocol.VLESS else "AmneziaWG",
        "status": "Подключено" if config.status == "active" else "Отключено",
        "createdAt": config.created_at,
        "lastUsedAt": "нет данных",
        "configUrl": f"/api/connections/{config.id}/config",
        "connectUrl": config.uri,
    }


@app.post("/auth/login")
def login(payload: LoginRequest) -> dict:
    demo_password = os.getenv("VPN_DEMO_PASSWORD", "demo")
    if payload.password != demo_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": os.getenv("VPN_API_TOKEN", "demo-token"), "tokenType": "Bearer"}


@app.get("/me")
def me(
    user_id: str = Depends(current_user_id),
    service: ConfigService = Depends(get_service),
) -> dict:
    user = service.get_current_user(user_id)
    return {
        "id": user.id,
        "name": user.name,
        "telegram": user.telegram,
        "email": user.email,
        "role": user.role,
        "avatarFallback": "".join(part[:1] for part in user.name.split()[:2]).upper() or "U",
    }


@app.get("/subscription")
def subscription(
    user_id: str = Depends(current_user_id),
    service: ConfigService = Depends(get_service),
) -> dict:
    return service.get_subscription(user_id)


@app.get("/servers")
def servers(service: ConfigService = Depends(get_service)) -> list[dict]:
    return [
        {
            "id": server.id,
            "name": server.name,
            "location": server.location,
            "protocols": [protocol.value for protocol in server.protocols],
        }
        for server in service.list_servers()
    ]


@app.get("/configs")
def configs(
    user_id: str = Depends(current_user_id),
    service: ConfigService = Depends(get_service),
) -> list[dict]:
    return [serialize_config(config, service) for config in service.list_configs(user_id)]


@app.post("/configs", status_code=201)
def create_config(
    payload: CreateConfigRequest,
    user_id: str = Depends(current_user_id),
    service: ConfigService = Depends(get_service),
) -> dict:
    protocol = Protocol.AMNEZIAWG if payload.protocol == "amneziawg" else Protocol.VLESS
    if payload.protocol == "auto" and payload.deviceType.lower() in {"роутер", "router"}:
        protocol = Protocol.AMNEZIAWG
    try:
        issued = service.create_config(
            user_id=user_id,
            device_name=payload.deviceName,
            device_type=payload.deviceType,
            protocol=protocol,
            server_id=payload.serverId,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_config(issued.config, service)


@app.get("/configs/{config_id}")
def config_detail(
    config_id: str,
    user_id: str = Depends(current_user_id),
    service: ConfigService = Depends(get_service),
) -> dict:
    try:
        return serialize_config(service.get_config(config_id, user_id), service)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/configs/{config_id}/qr")
def config_qr(
    config_id: str,
    user_id: str = Depends(current_user_id),
    service: ConfigService = Depends(get_service),
) -> dict:
    try:
        return {"value": service.get_config(config_id, user_id).uri}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/configs/{config_id}/download")
def config_download(
    config_id: str,
    user_id: str = Depends(current_user_id),
    service: ConfigService = Depends(get_service),
) -> Response:
    try:
        config = service.get_config(config_id, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    filename = (
        f"{config.display_name}.conf"
        if config.protocol == Protocol.AMNEZIAWG
        else f"{config.display_name}.txt"
    )
    return Response(
        config.config_text,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/configs/{config_id}/revoke")
def revoke_config(
    config_id: str,
    user_id: str = Depends(current_user_id),
    service: ConfigService = Depends(get_service),
) -> dict:
    try:
        return serialize_config(service.revoke_config(config_id, user_id), service)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

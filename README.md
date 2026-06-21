# Proxy Manager

Project documentation:

- [English](README.en.md)
- [Русский](README.ru.md)

The public repository contains application source code, tests, safe examples,
and operational scripts. Production inventory and encrypted deployment
configuration belong in the private infrastructure repository.

The user web cabinet MVP lives in [`web/`](web/). It is a Next.js application
with mock API adapters prepared for future VLESS Reality and AmneziaWG backend
integration.

Shared VPN issuing logic lives in [`vpn_service/`](vpn_service/):

```text
Telegram Bot ─┐
              ├── ConfigService
Web UI ───────┘
                    ├── VlessProvider
                    ├── AmneziaWgProvider
                    └── MockNodeAgent
```

Run the local API:

```bash
python -m uvicorn vpn_service.api:app --reload --port 8000
```

The existing Telegram admin bot remains unchanged. The new service is ready to
be wired into bot handlers and the web cabinet without replacing the current
Telemt/HTTP/SOCKS5 administration flow.

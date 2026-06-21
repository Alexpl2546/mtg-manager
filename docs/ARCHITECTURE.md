# Architecture

## Components

- `bot.py` contains Telegram handlers and delegates protocol operations.
- `providers/` implements Telemt, HTTP, and SOCKS5 backends.
- `vpn_service/` contains shared user-facing VPN configuration issuing logic
  for VLESS Reality and AmneziaWG.
- `web/` contains the Next.js user cabinet and proxies API calls to
  `vpn_service.api` when `VPN_BACKEND_URL` is configured.
- `utils/storage.py` stores runtime metadata using atomic JSON replacement.
- `utils/threeproxy.py` renders and activates HTTP/SOCKS5 configuration.
- `scripts/` contains audited operational, backup, migration, and deployment tools.

## Runtime ownership

| Data | Owner | Location |
| --- | --- | --- |
| Bot token and admin IDs | system administrator | `/opt/proxy-manager/.env` |
| Client metadata | Proxy Manager | `/opt/proxy-manager/data/*.json` |
| Telemt users and secrets | Telemt | `/etc/telemt/telemt.toml` |
| HTTP/SOCKS5 runtime config | 3proxy | `/etc/3proxy/3proxy.cfg` |

Runtime data is not source code and must not be committed.

## Telemt consistency

Telemt is the authoritative store for Telemt users. Proxy Manager keeps a local
metadata index so the bot can display existing clients. The reconciliation
script compares both stores without deleting or rotating users automatically.

## Deployment

Releases are immutable source archives without `.env` or runtime JSON. The
deployment script validates data, creates a backup, prepares the virtual
environment, verifies Telemt readiness, installs the release, and rolls back on
failure.

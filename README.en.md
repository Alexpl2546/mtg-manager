# Proxy Manager

A Telegram bot and operational toolkit for managing MTG/MTProto, Telemt, HTTP,
and SOCKS5 proxies on a single Linux server.

Русская версия: [README.ru.md](README.ru.md)

## Repository Purpose

This is the public application repository. It contains source code, tests,
safe configuration examples, and operational scripts. Production secrets,
live client databases, VPS audits, backup archives, and active connection links
must never be stored here.

The related private `mtg-manager-infrastructure` repository contains Ansible
environment configuration and SOPS-encrypted secrets only. Runtime client data
must not be committed there either.

## Features

- Bot access restricted to Telegram IDs listed in `ADMIN_IDS`.
- Create, inspect, and delete MTG, Telemt, HTTP, and SOCKS5 clients.
- Select Fake TLS domains for MTG and Telemt.
- Allocate free ports to isolated MTG containers.
- Synchronize HTTP/SOCKS5 users into a shared 3proxy configuration.
- Manage Telemt through its official Control API without restarting it for
  every user change.
- Atomically replace local JSON indexes.
- Back up, health-check, and automatically roll back production deployments.
- Audit, harden, and perform verified Telemt upgrades.

## Architecture

```text
Telegram administrator
        |
        v
     bot.py
        |
        +-- MTGProvider ------> Docker + /opt/mtg-clients/
        +-- TelemtProvider ---> Telemt Control API
        +-- HTTPProvider -----+
        +-- SOCKS5Provider ---+-> 3proxy configuration
        |
        +-- data/*.json (local index and settings)
```

`bot.py` owns the Telegram interface and delegates protocol operations to the
appropriate provider. Providers manage external services and persist local
metadata through `utils/storage.py`.

Telemt is authoritative for its users. The local `telemt_clients.json` is an
index used by the bot. Reconciliation only compares the two stores and never
deletes users automatically.

## Artifact Map

### Repository Root

| Artifact | Purpose |
| --- | --- |
| `bot.py` | Aiogram entry point and handlers for protocol selection, client lifecycle, and domain changes. |
| `config.py` | Loads `BOT_TOKEN`, `ADMIN_IDS`, and Telemt API settings from the environment. |
| `requirements.txt` | Production Python dependencies. |
| `requirements-dev.txt` | Test and lint tools. |
| `pyproject.toml` | Ruff and pytest configuration. |
| `.env.example` | Safe environment variable template. |
| `.gitignore` | Excludes secrets, runtime JSON, archives, logs, and local environments. |
| `.gitattributes` | Normalizes line endings and file attributes. |
| `SECURITY.md` | Vulnerability reporting and secret-handling policy. |
| `LICENSE` | Project license. |

### `providers/`

| Artifact | Purpose |
| --- | --- |
| `base.py` | Abstract provider contract: create, delete, get, list, and health. |
| `mtg_manager.py` | Writes MTG configuration, starts an isolated Docker container, and removes clients. |
| `telemt_manager.py` | Telemt Control API client, readiness checks, reconciliation, and user management. |
| `http_manager.py` | Generates HTTP proxy credentials and updates 3proxy. |
| `socks5_manager.py` | Generates SOCKS5 credentials and updates 3proxy. |
| `__init__.py` | Marks the directory as a Python package. |

### `utils/`

| Artifact | Purpose |
| --- | --- |
| `auth.py` | Middleware denying Telegram users outside `ADMIN_IDS`. |
| `keyboards.py` | Reply and inline keyboards for the bot UI. |
| `ports.py` | Finds free MTG ports while respecting system and reserved ports. |
| `state.py` | Small in-memory dialogue state: selected protocol and pending action. |
| `storage.py` | Reads JSON and replaces files atomically. |
| `threeproxy.py` | Collects users, renders configuration, and safely reloads 3proxy. |
| `validation.py` | Normalizes and validates client names. |

### `scripts/`

| Artifact | Purpose |
| --- | --- |
| `deploy-proxy-manager.sh` | Transactional release deployment with JSON validation, backup, a new venv, health checks, and rollback. |
| `post-deploy-check.sh` | Reports services, configuration, client indexes, Telemt reconciliation, and recent errors. |
| `backup-runtime.sh` | Creates a root-only backup of live configuration and runtime data. |
| `audit-telemt.sh` | Collects safe Telemt diagnostics before changes. |
| `upgrade-telemt.sh` | Downloads an official release, verifies SHA-256, backs up, and rolls back Telemt upgrades. |
| `harden-telemt.sh` | Applies systemd hardening, required capabilities, and journald link suppression. |
| `reconcile-telemt.py` | Read-only comparison of the local index and Telemt users. |
| `import-telemt-missing.py` | Controlled import of missing local metadata from Telemt. |
| `install-mtproto.sh` | Installs an MTG client with isolated configuration and container. |
| `delete-mtproto.sh` | Removes an MTG container and its files. |
| `archive-legacy-proxy.sh` | Archives a legacy proxy installation before migration. |

### `data/`

`settings.json.example` documents the safe runtime settings shape: Fake TLS
domains and public HTTP/SOCKS5 hosts and ports. The live
`data/settings.json` is ignored by Git.

The application creates these runtime files:

| File | Contents |
| --- | --- |
| `mtg_clients.json` | MTG client metadata and allocated ports. |
| `telemt_clients.json` | Local Telemt user and connection-link index. |
| `http_clients.json` | HTTP proxy names, usernames, and passwords. |
| `socks5_clients.json` | SOCKS5 names, usernames, and passwords. |
| `settings.json` | Live domains, addresses, and ports. |

All live files can contain secrets and are excluded from Git.

### Tests and CI

| Artifact | Purpose |
| --- | --- |
| `tests/test_config.py` | Admin parsing and required configuration. |
| `tests/test_storage.py` | Atomic JSON writes and reads. |
| `tests/test_telemt.py` | Telemt response shapes and Fake TLS link extraction. |
| `tests/test_validation.py` | Client name normalization and validation. |
| `.github/workflows/ci.yml` | Runs tests and Ruff in GitHub Actions. |

### Additional Documentation

- `docs/ARCHITECTURE.md` describes data ownership.
- `docs/OPERATIONS.md` covers health checks, backups, logs, and rollback.
- `SECURITY.md` defines sensitive-data restrictions.

## Data Ownership

| Data | Authority | Production location |
| --- | --- | --- |
| Bot token and administrator IDs | System administrator | `/opt/proxy-manager/.env` |
| Local client metadata | Proxy Manager | `/opt/proxy-manager/data/*.json` |
| Telemt users and secrets | Telemt | `/etc/telemt/telemt.toml` |
| HTTP/SOCKS5 runtime | 3proxy | `/etc/3proxy/3proxy.cfg` |
| MTG client configuration | MTG provider | `/opt/mtg-clients/<name>/` |
| Proxy Manager backups | Deploy script | `/var/backups/proxy-manager/<timestamp>/` |
| Telemt backups | Upgrade script | `/var/backups/telemt/<timestamp>/` |

## Local Development

Python 3.10 or later is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
cp data/settings.json.example data/settings.json
```

Populate `.env` without adding it to Git:

```dotenv
BOT_TOKEN=telegram_bot_token
ADMIN_IDS=123456789
TELEMT_API_URL=http://127.0.0.1:9091
TELEMT_API_AUTH=
```

Run checks:

```bash
python -m pytest -q
python -m ruff check .
```

Run the bot:

```bash
set -a
source .env
set +a
python bot.py
```

Full provider operations expect a Linux host with Docker, systemd, Telemt, and
3proxy. Tests and lint are safe on a regular development workstation.

## Production Deployment

A release archive is built from tracked public files and must not contain
`.env`, live `data/*.json`, logs, or backups.

```bash
sudo bash scripts/deploy-proxy-manager.sh \
  /tmp/proxy-manager-release.tar.gz
sudo bash /opt/proxy-manager/scripts/post-deploy-check.sh
```

The private infrastructure repository automates upload of a verified archive
and execution of these commands through Ansible.

## Security Rules

- Never commit `.env`, runtime JSON, or active proxy configuration.
- Do not publish server IPs, client names, passwords, or connection links.
- Backup and audit artifacts can contain secrets; keep them encrypted.
- Do not change the Telemt `secret` or `censorship.tls_domain` without a
  migration because existing links will stop working.
- When Telemt and the local index differ, run read-only reconciliation before
  deleting any user.

## Git Workflow

`main` is the stable branch. Development happens in task branches:

```bash
git switch main
git pull --ff-only origin main
git switch -c codex/<task>
python -m pytest -q
python -m ruff check .
git push -u origin codex/<task>
```

Merge to `main` and deploy to production only after review.

## Status on June 15, 2026

- Public `main`: `9f66ba1` (`Modernize proxy manager architecture`).
- Production was deployed from that state.
- `proxy-manager`, `telemt`, and `3proxy` were active after deployment.
- The local index and Telemt matched: 17 users out of 17.
- All 10 local tests and Ruff passed.

User counts and production health are a point-in-time snapshot, not
configuration that application code should depend on.

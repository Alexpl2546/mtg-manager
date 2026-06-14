# Operations

## Health check

```bash
sudo bash /opt/proxy-manager/scripts/post-deploy-check.sh
```

## Runtime backup

```bash
sudo bash /opt/proxy-manager/scripts/backup-runtime.sh
```

Backups contain live credentials and must remain readable only by root.

## Telemt reconciliation

```bash
set -a
source /opt/proxy-manager/.env
set +a
/opt/proxy-manager/venv/bin/python \
  /opt/proxy-manager/scripts/reconcile-telemt.py
```

The command is read-only. A mismatch must be investigated before any deletion
or secret rotation.

## Logs

```bash
journalctl -u proxy-manager -n 100 --no-pager
journalctl -u telemt -n 100 --no-pager
journalctl -u 3proxy -n 100 --no-pager
```

Do not paste logs publicly without checking for credentials and connection
links.

## Rollback

Deployment backups are stored in `/var/backups/proxy-manager/<timestamp>`.
Telemt binary/config backups are stored in `/var/backups/telemt/<timestamp>`.

#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="${PROXY_MANAGER_DIR:-/opt/proxy-manager}"
BACKUP_ROOT="${PROXY_MANAGER_BACKUP_ROOT:-/var/backups/proxy-manager}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
destination="$BACKUP_ROOT/runtime-$timestamp"

if [[ "$EUID" -ne 0 ]]; then
  echo "Run as root" >&2
  exit 1
fi

mkdir -p "$destination"

for filename in \
  settings.json \
  mtg_clients.json \
  telemt_clients.json \
  http_clients.json \
  socks5_clients.json
do
  path="$PROJECT_DIR/data/$filename"
  [[ -f "$path" ]] || {
    echo "Runtime file not found: $path" >&2
    exit 1
  }
  python3 -m json.tool "$path" >/dev/null
done

cp -a "$PROJECT_DIR/data" "$destination/data"
cp -a "$PROJECT_DIR/.env" "$destination/.env"
cp -a /etc/telemt/telemt.toml "$destination/telemt.toml"
cp -a /etc/3proxy/3proxy.cfg "$destination/3proxy.cfg"
chmod -R go-rwx "$destination"

echo "Runtime backup created: $destination"

#!/usr/bin/env bash
set -Eeuo pipefail

CURRENT_DIR="${PROXY_MANAGER_DIR:-/opt/proxy-manager}"
BACKUP_ROOT="${PROXY_MANAGER_BACKUP_ROOT:-/var/backups/proxy-manager}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
archive_dir="$BACKUP_ROOT/legacy-$timestamp"

if [[ "$EUID" -ne 0 ]]; then
  echo "Run as root" >&2
  exit 1
fi

[[ -d "$CURRENT_DIR" ]] || {
  echo "Current project not found: $CURRENT_DIR" >&2
  exit 1
}

for service in proxy-manager telemt 3proxy; do
  systemctl is-active --quiet "$service" || {
    echo "Active service check failed: $service" >&2
    exit 1
  }
done

runtime_files=(
  settings.json
  mtg_clients.json
  telemt_clients.json
  http_clients.json
  socks5_clients.json
)
for filename in "${runtime_files[@]}"; do
  path="$CURRENT_DIR/data/$filename"
  [[ -f "$path" ]] || {
    echo "Current runtime file not found: $path" >&2
    exit 1
  }
  python3 -m json.tool "$path" >/dev/null || {
    echo "Current runtime JSON is invalid: $path" >&2
    exit 1
  }
done

telemt_ready="$(
  curl -fsS --max-time 5 http://127.0.0.1:9091/v1/health/ready
)"
python3 -c \
  'import json,sys; raise SystemExit(0 if json.loads(sys.argv[1]).get("data", {}).get("ready") else 1)' \
  "$telemt_ready"

mtg_count="$(
  python3 - "$CURRENT_DIR/data/mtg_clients.json" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(len(data))
PY
)"
if [[ "$mtg_count" != "0" ]]; then
  echo "Current MTG database is not empty; refusing to archive /opt/mtg-clients" >&2
  exit 1
fi

active_mtg_containers="$(
  docker ps -a --filter 'name=mtg-' --format '{{.Names}}' 2>/dev/null | wc -l
)"
if [[ "$active_mtg_containers" != "0" ]]; then
  echo "MTG containers still exist; refusing cleanup" >&2
  exit 1
fi

mkdir -p "$archive_dir/files" "$archive_dir/systemd"
chmod 0700 "$archive_dir"

manifest="$archive_dir/MANIFEST.txt"
{
  echo "Created: $(date -u --iso-8601=seconds)"
  echo "Host: $(hostname)"
  echo "Current project preserved: $CURRENT_DIR"
  echo "Telemt config preserved: /etc/telemt/telemt.toml"
  echo "3proxy config preserved: /etc/3proxy/3proxy.cfg"
  echo
  echo "Archived paths:"
} >"$manifest"

archive_path() {
  local path="$1"
  local relative="${path#/}"
  if [[ ! -e "$path" ]]; then
    return
  fi

  mkdir -p "$archive_dir/files/$(dirname "$relative")"
  mv -- "$path" "$archive_dir/files/$relative"
  echo "$path" >>"$manifest"
}

if systemctl list-unit-files mtg-bot.service --no-legend 2>/dev/null |
  grep -q '^mtg-bot.service'
then
  systemctl disable --now mtg-bot.service 2>/dev/null || true
  if [[ -f /etc/systemd/system/mtg-bot.service ]]; then
    mv /etc/systemd/system/mtg-bot.service \
      "$archive_dir/systemd/mtg-bot.service"
    echo "/etc/systemd/system/mtg-bot.service" >>"$manifest"
  fi
fi

archive_path /opt/mtg-bot
archive_path /opt/mtg-clients

legacy_data=(
  mtproto_clients.json
  mtproto_clients_backup.json
  mtg_clients_backup.json
)
mkdir -p "$archive_dir/files/opt/proxy-manager/data"
for filename in "${legacy_data[@]}"; do
  path="$CURRENT_DIR/data/$filename"
  if [[ -e "$path" ]]; then
    mv -- "$path" "$archive_dir/files/opt/proxy-manager/data/$filename"
    echo "$path" >>"$manifest"
  fi
done

legacy_scripts=(
  telemt_add_user.sh
  telemt_delete_user.sh
  telemt_list_users.sh
  http_add_user.sh
  http_delete_user.sh
  socks5_add_user.sh
  socks5_delete_user.sh
)
mkdir -p "$archive_dir/files/opt/proxy-manager/scripts"
for filename in "${legacy_scripts[@]}"; do
  path="$CURRENT_DIR/scripts/$filename"
  if [[ -e "$path" ]]; then
    mv -- "$path" "$archive_dir/files/opt/proxy-manager/scripts/$filename"
    echo "$path" >>"$manifest"
  fi
done

systemctl daemon-reload

for service in proxy-manager telemt 3proxy; do
  systemctl is-active --quiet "$service" || {
    echo "Service became inactive after cleanup: $service" >&2
    exit 1
  }
done

chmod -R go-rwx "$archive_dir"
echo "Legacy proxy files archived successfully"
echo "Archive: $archive_dir"
cat "$manifest"

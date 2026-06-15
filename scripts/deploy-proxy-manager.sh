#!/usr/bin/env bash
set -Eeuo pipefail

ARCHIVE_PATH="${1:-/tmp/proxy-manager-release.tar.gz}"
INSTALL_DIR="${PROXY_MANAGER_DIR:-/opt/proxy-manager}"
SERVICE_NAME="${PROXY_MANAGER_SERVICE:-proxy-manager}"
BACKUP_ROOT="${PROXY_MANAGER_BACKUP_ROOT:-/var/backups/proxy-manager}"

if [[ "$EUID" -ne 0 ]]; then
  echo "Run as root" >&2
  exit 1
fi

for command in tar python3 systemctl; do
  command -v "$command" >/dev/null || {
    echo "Required command not found: $command" >&2
    exit 1
  }
done

[[ -f "$ARCHIVE_PATH" ]] || {
  echo "Release archive not found: $ARCHIVE_PATH" >&2
  exit 1
}
[[ -d "$INSTALL_DIR" ]] || {
  echo "Install directory not found: $INSTALL_DIR" >&2
  exit 1
}
[[ -f "$INSTALL_DIR/.env" ]] || {
  echo "Environment file not found: $INSTALL_DIR/.env" >&2
  exit 1
}

archive_files="$(tar -tzf "$ARCHIVE_PATH")"
if grep -Eq '(^/|(^|/)\.\.(/|$))' <<<"$archive_files"; then
  echo "Archive contains unsafe paths" >&2
  exit 1
fi
if grep -E '(^|/)\.env$|(^|/)data/[^/]+\.json$' <<<"$archive_files" |
  grep -Evq '(^|/)data/settings\.json\.example$'
then
  echo "Archive contains runtime data or secrets" >&2
  exit 1
fi

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_dir="$BACKUP_ROOT/$timestamp"
staging_dir="$(mktemp -d)"
mkdir -p "$backup_dir"

cleanup() {
  rm -rf -- "$staging_dir"
  if [[ -n "${new_venv:-}" && -d "$new_venv" ]]; then
    rm -rf -- "$new_venv"
  fi
}
trap cleanup EXIT

echo "Validating runtime JSON..."
runtime_files=(
  "settings.json"
  "telemt_clients.json"
  "http_clients.json"
  "socks5_clients.json"
)
for filename in "${runtime_files[@]}"; do
  path="$INSTALL_DIR/data/$filename"
  if [[ ! -f "$path" ]]; then
    if [[ "$filename" == "settings.json" ]]; then
      echo "Required runtime file not found: $path" >&2
      exit 1
    fi
    printf '{}\n' >"$path"
  fi
  python3 -m json.tool "$path" >/dev/null || {
    echo "Invalid runtime JSON: $path" >&2
    exit 1
  }
done

echo "Creating backup..."
tar \
  --exclude='.git' \
  --exclude='venv' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  -czf "$backup_dir/project.tar.gz" \
  -C "$INSTALL_DIR" .
systemctl cat "$SERVICE_NAME" >"$backup_dir/service.before"
override_dir="/etc/systemd/system/${SERVICE_NAME}.service.d"
override_path="$override_dir/runtime.conf"
if [[ -f "$override_path" ]]; then
  cp -a "$override_path" "$backup_dir/runtime.conf.before"
else
  touch "$backup_dir/runtime.conf.absent"
fi

tar -xzf "$ARCHIVE_PATH" -C "$staging_dir"
[[ -f "$staging_dir/bot.py" && -f "$staging_dir/requirements.txt" ]] || {
  echo "Invalid release archive" >&2
  exit 1
}

python3 -m compileall -q "$staging_dir"

echo "Preparing virtual environment..."
new_venv="$INSTALL_DIR/venv.new-$timestamp"
previous_venv="$INSTALL_DIR/venv.previous-$timestamp"
python3 -m venv "$new_venv"
"$new_venv/bin/python" -m pip install \
  --disable-pip-version-check \
  --upgrade pip
"$new_venv/bin/python" -m pip install \
  --disable-pip-version-check \
  -r "$staging_dir/requirements.txt"

rollback() {
  echo "Deployment failed, rolling back..."
  systemctl stop "$SERVICE_NAME" || true
  tar -xzf "$backup_dir/project.tar.gz" -C "$INSTALL_DIR"
  if [[ -f "$backup_dir/runtime.conf.before" ]]; then
    mkdir -p "$override_dir"
    cp -a "$backup_dir/runtime.conf.before" "$override_path"
  else
    rm -f -- "$override_path"
  fi
  rm -rf -- "$INSTALL_DIR/venv"
  if [[ -d "$previous_venv" ]]; then
    mv -- "$previous_venv" "$INSTALL_DIR/venv"
  fi
  systemctl daemon-reload
  systemctl start "$SERVICE_NAME" || true
}
trap rollback ERR

echo "Installing release..."
systemctl stop "$SERVICE_NAME"
if [[ -d "$INSTALL_DIR/venv" ]]; then
  mv -- "$INSTALL_DIR/venv" "$previous_venv"
fi
mv -- "$new_venv" "$INSTALL_DIR/venv"
tar -xzf "$ARCHIVE_PATH" -C "$INSTALL_DIR"
rm -f -- \
  "$INSTALL_DIR/providers/mtg_manager.py" \
  "$INSTALL_DIR/scripts/install-mtproto.sh" \
  "$INSTALL_DIR/scripts/delete-mtproto.sh" \
  "$INSTALL_DIR/scripts/archive-legacy-proxy.sh" \
  "$INSTALL_DIR/utils/ports.py" \
  "$INSTALL_DIR/data/mtg_clients.json" \
  "$INSTALL_DIR/data/mtproto_clients.json" \
  "$INSTALL_DIR/data/mtproto_clients_backup.json" \
  "$INSTALL_DIR/data/mtg_clients_backup.json"
rm -rf -- "$INSTALL_DIR/data/mtg-clients"
python3 - "$INSTALL_DIR/data/settings.json" <<'PY'
import json
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
settings = json.loads(path.read_text(encoding="utf-8"))
if settings.pop("mtg", None) is not None:
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary_path, path)
PY
chmod +x "$INSTALL_DIR"/scripts/*.sh 2>/dev/null || true

mkdir -p "$override_dir"
cat >"$override_path" <<EOF
[Service]
EnvironmentFile=
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/bot.py
EOF

systemctl daemon-reload

set -a
source "$INSTALL_DIR/.env"
set +a
(
  cd "$INSTALL_DIR"
  "$INSTALL_DIR/venv/bin/python" -c \
    'from config import load_settings; from providers.telemt_manager import TelemtProvider; load_settings(); print(TelemtProvider().health())'
)

systemctl start "$SERVICE_NAME"
sleep 3
systemctl is-active --quiet "$SERVICE_NAME"

trap - ERR
rm -rf -- "$previous_venv"
echo "Proxy Manager deployed successfully"
echo "Backup: $backup_dir"
systemctl status "$SERVICE_NAME" --no-pager

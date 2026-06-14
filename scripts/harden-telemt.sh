#!/usr/bin/env bash
set -Eeuo pipefail

SERVICE_NAME="${TELEMT_SERVICE_NAME:-telemt}"
CONFIG_PATH="${TELEMT_CONFIG_PATH:-/etc/telemt/telemt.toml}"
OVERRIDE_DIR="/etc/systemd/system/${SERVICE_NAME}.service.d"
OVERRIDE_PATH="${OVERRIDE_DIR}/capabilities.conf"

if [[ "$EUID" -ne 0 ]]; then
  echo "Run as root" >&2
  exit 1
fi

[[ -f "$CONFIG_PATH" ]] || {
  echo "Config not found: $CONFIG_PATH" >&2
  exit 1
}

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_dir="/var/backups/telemt/$timestamp-hardening"
mkdir -p "$backup_dir" "$OVERRIDE_DIR"
cp -a "$CONFIG_PATH" "$backup_dir/telemt.toml"
systemctl cat "$SERVICE_NAME" >"$backup_dir/telemt.service"

cat >"$OVERRIDE_PATH" <<'EOF'
[Service]
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
NoNewPrivileges=true
EOF

python3 - "$CONFIG_PATH" <<'PY'
import os
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
replacement = "show_link = []"

if re.search(r"(?m)^\s*show_link\s*=", text):
    updated = re.sub(
        r"(?m)^\s*show_link\s*=.*$",
        replacement,
        text,
        count=1,
    )
else:
    updated = replacement + "\n\n" + text

temporary = path.with_suffix(path.suffix + ".tmp")
temporary.write_text(updated, encoding="utf-8")
os.chmod(temporary, path.stat().st_mode)
os.replace(temporary, path)
PY

systemctl daemon-reload
systemctl restart "$SERVICE_NAME"

for _ in {1..90}; do
  if response="$(curl -fsS --max-time 3 http://127.0.0.1:9091/v1/health/ready 2>/dev/null)" &&
    python3 -c \
      'import json,sys; raise SystemExit(0 if json.loads(sys.argv[1]).get("data", {}).get("ready") else 1)' \
      "$response" 2>/dev/null
  then
    break
  fi
  sleep 1
done

systemctl is-active --quiet "$SERVICE_NAME"
systemctl show "$SERVICE_NAME" \
  --property=AmbientCapabilities,CapabilityBoundingSet,NoNewPrivileges \
  --no-pager

echo "Telemt hardening applied"
echo "Backup: $backup_dir"

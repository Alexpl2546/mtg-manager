#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="${PROXY_MANAGER_DIR:-/opt/proxy-manager}"
SERVICE_NAME="${PROXY_MANAGER_SERVICE:-proxy-manager}"

echo "=== SERVICES ==="
for service in "$SERVICE_NAME" telemt 3proxy; do
  printf '%s: ' "$service"
  systemctl is-active "$service"
done

echo "=== MANAGER ==="
systemctl show "$SERVICE_NAME" \
  --property=ExecStart,EnvironmentFiles,MainPID,ActiveEnterTimestamp \
  --no-pager
"$PROJECT_DIR/venv/bin/python" -c \
  'import aiogram; print("aiogram:", aiogram.__version__)'

echo "=== CONFIG ==="
if grep -Eq '^ADMIN_IDS=[0-9]+(,[0-9]+)*$' "$PROJECT_DIR/.env"; then
  echo "ADMIN_IDS: configured"
else
  echo "ADMIN_IDS: invalid or missing"
  exit 1
fi

echo "=== DATA ==="
python3 - "$PROJECT_DIR/data" <<'PY'
import json
import sys
from pathlib import Path

data_dir = Path(sys.argv[1])
for filename in (
    "mtg_clients.json",
    "telemt_clients.json",
    "http_clients.json",
    "socks5_clients.json",
):
    data = json.loads((data_dir / filename).read_text(encoding="utf-8"))
    print(f"{filename}: {len(data)}")
PY

echo "=== TELEMT ==="
set -a
source "$PROJECT_DIR/.env"
set +a
"$PROJECT_DIR/venv/bin/python" "$PROJECT_DIR/scripts/reconcile-telemt.py" || true
curl -fsS --max-time 5 http://127.0.0.1:9091/v1/health/ready |
  python3 -c '
import json, sys
data = json.load(sys.stdin).get("data", {})
print("ready:", data.get("ready"))
print("healthy_upstreams:", data.get("healthy_upstreams"))
'

echo "=== RECENT MANAGER ERRORS ==="
journalctl -u "$SERVICE_NAME" --since "15 minutes ago" \
  --priority=warning --no-pager || true

#!/usr/bin/env bash
set -Eeuo pipefail

SERVICE_NAME="${TELEMT_SERVICE_NAME:-telemt}"
CONFIG_PATH="${TELEMT_CONFIG_PATH:-/etc/telemt/telemt.toml}"
API_URL="${TELEMT_API_URL:-http://127.0.0.1:9091}"
API_AUTH="${TELEMT_API_AUTH:-}"

curl_args=(-fsS --max-time 5)
if [[ -n "$API_AUTH" ]]; then
  curl_args+=(-H "Authorization: $API_AUTH")
fi

echo "=== SERVICE ==="
systemctl is-enabled "$SERVICE_NAME" 2>/dev/null || true
systemctl is-active "$SERVICE_NAME" 2>/dev/null || true
systemctl show "$SERVICE_NAME" \
  --property=User,Group,ExecStart,WorkingDirectory,FragmentPath \
  --no-pager 2>/dev/null || true

echo "=== BINARY ==="
binary_path="$(
  systemctl show "$SERVICE_NAME" --property=ExecStart --value 2>/dev/null |
    sed -n 's/.*path=\([^ ;}]*\).*/\1/p' |
    head -n 1
)"
if [[ -n "$binary_path" && -x "$binary_path" ]]; then
  "$binary_path" --version 2>&1 || true
  sha256sum "$binary_path"
else
  echo "binary: not detected"
fi

echo "=== CONFIG SHAPE ==="
if [[ -f "$CONFIG_PATH" ]]; then
  python3 - "$CONFIG_PATH" <<'PY'
import re
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding="utf-8")
section = ""
users = 0

for raw_line in text.splitlines():
    line = raw_line.strip()
    if line.startswith("[") and line.endswith("]"):
        section = line
    elif section == "[access.users]" and re.match(r'^[A-Za-z0-9_.-]+\s*=', line):
        users += 1

def value(pattern):
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1) if match else "not-set"

print("users:", users)
print("server_port:", value(r"^\s*port\s*=\s*(\d+)\s*$"))
print("tls_domain:", value(r'^\s*tls_domain\s*=\s*"([^"]+)"'))
print("api_listen:", value(r'^\s*listen\s*=\s*"([^"]+)"'))
print("config_sha256: calculated below")
PY
  sha256sum "$CONFIG_PATH"
else
  echo "config: not found"
fi

echo "=== API ==="
curl "${curl_args[@]}" "$API_URL/v1/system/info" 2>/dev/null |
  python3 -c '
import json, sys
data = json.load(sys.stdin)
info = data.get("data", {})
for key in ("version", "git_sha", "uptime_seconds", "config_path", "config_hash"):
    if key in info:
        print(f"{key}: {info[key]}")
' || echo "API system info: unavailable"

curl "${curl_args[@]}" "$API_URL/v1/health/ready" 2>/dev/null |
  python3 -c '
import json, sys
data = json.load(sys.stdin)
ready = data.get("data", {})
print("ready:", ready.get("ready"))
print("reason:", ready.get("reason", "none"))
print("healthy_upstreams:", ready.get("healthy_upstreams", "unknown"))
' || echo "API readiness: unavailable"

echo "=== RECENT LOGS ==="
journalctl -u "$SERVICE_NAME" -n 80 --no-pager |
  sed -E 's/(secret|password|token)([=: ]+)[^ ]+/\1\2[REDACTED]/Ig'

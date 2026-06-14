#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="${1:-3.4.18}"
SERVICE_NAME="${TELEMT_SERVICE_NAME:-telemt}"
CONFIG_PATH="${TELEMT_CONFIG_PATH:-/etc/telemt/telemt.toml}"
API_URL="${TELEMT_API_URL:-http://127.0.0.1:9091}"
API_AUTH="${TELEMT_API_AUTH:-}"
EXPECTED_VERSION="3.4.18"
EXPECTED_SHA256="9abc5751661c71da7c22a872ce6842a2591eb68d7d7a2a2ce574741ae2fbeb25"

if [[ "$EUID" -ne 0 ]]; then
  echo "Run as root" >&2
  exit 1
fi

if [[ "$VERSION" != "$EXPECTED_VERSION" ]]; then
  echo "This script is pinned to Telemt $EXPECTED_VERSION" >&2
  exit 1
fi

for command in curl tar sha256sum systemctl python3; do
  command -v "$command" >/dev/null || {
    echo "Required command not found: $command" >&2
    exit 1
  }
done

[[ -f "$CONFIG_PATH" ]] || {
  echo "Config not found: $CONFIG_PATH" >&2
  exit 1
}

binary_path="$(
  systemctl show "$SERVICE_NAME" --property=ExecStart --value |
    sed -n 's/.*path=\([^ ;}]*\).*/\1/p' |
    head -n 1
)"

[[ -n "$binary_path" && -x "$binary_path" ]] || {
  echo "Unable to detect Telemt binary from systemd" >&2
  exit 1
}

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_dir="/var/backups/telemt/$timestamp"
temp_dir="$(mktemp -d)"
asset="telemt-x86_64-linux-gnu.tar.gz"
download_url="https://github.com/telemt/telemt/releases/download/$VERSION/$asset"

cleanup() {
  rm -rf -- "$temp_dir"
}
trap cleanup EXIT

mkdir -p "$backup_dir"
cp -a "$binary_path" "$backup_dir/telemt"
cp -a "$CONFIG_PATH" "$backup_dir/telemt.toml"
systemctl cat "$SERVICE_NAME" >"$backup_dir/telemt.service"

config_hash_before="$(sha256sum "$CONFIG_PATH" | awk '{print $1}')"
api_args=(-fsS --max-time 5)
if [[ -n "$API_AUTH" ]]; then
  api_args+=(-H "Authorization: $API_AUTH")
fi
users_before="$(
  curl "${api_args[@]}" "$API_URL/v1/users" 2>/dev/null |
    python3 -c 'import json,sys; print(len(json.load(sys.stdin).get("data", [])))' ||
    echo unknown
)"

echo "Downloading Telemt $VERSION..."
curl -fL --retry 3 "$download_url" -o "$temp_dir/$asset"
echo "$EXPECTED_SHA256  $temp_dir/$asset" | sha256sum -c -
tar -xzf "$temp_dir/$asset" -C "$temp_dir"

candidate="$(find "$temp_dir" -type f -name telemt -print -quit)"
[[ -n "$candidate" ]] || {
  echo "Telemt binary not found in release archive" >&2
  exit 1
}
chmod 0755 "$candidate"
"$candidate" --version

rollback() {
  echo "Upgrade failed, rolling back..."
  install -m 0755 "$backup_dir/telemt" "$binary_path"
  cp -a "$backup_dir/telemt.toml" "$CONFIG_PATH"
  systemctl restart "$SERVICE_NAME" || true
}
trap rollback ERR

systemctl stop "$SERVICE_NAME"
install -m 0755 "$candidate" "$binary_path"
systemctl start "$SERVICE_NAME"

for _ in {1..90}; do
  if readiness="$(
    curl "${api_args[@]}" "$API_URL/v1/health/ready" 2>/dev/null
  )" && python3 -c \
    'import json,sys; raise SystemExit(0 if json.loads(sys.argv[1]).get("data", {}).get("ready") else 1)' \
    "$readiness" 2>/dev/null
  then
    break
  fi
  sleep 1
done

systemctl is-active --quiet "$SERVICE_NAME"
curl "${api_args[@]}" "$API_URL/v1/health/ready" |
  python3 -c 'import json,sys; raise SystemExit(0 if json.load(sys.stdin).get("data", {}).get("ready") else 1)'
running_version="$(
  curl "${api_args[@]}" "$API_URL/v1/system/info" |
    python3 -c 'import json,sys; print(json.load(sys.stdin).get("data", {}).get("version", ""))'
)"
[[ "$running_version" == "$VERSION" ]] || {
  echo "Unexpected running version: $running_version" >&2
  false
}

config_hash_after="$(sha256sum "$CONFIG_PATH" | awk '{print $1}')"
[[ "$config_hash_before" == "$config_hash_after" ]] || {
  echo "Config changed unexpectedly" >&2
  false
}

users_after="$(
  curl "${api_args[@]}" "$API_URL/v1/users" |
    python3 -c 'import json,sys; print(len(json.load(sys.stdin).get("data", [])))'
)"
if [[ "$users_before" != "unknown" && "$users_before" != "$users_after" ]]; then
  echo "User count changed: $users_before -> $users_after" >&2
  false
fi

trap - ERR
echo "Telemt upgraded to $VERSION"
echo "Config unchanged: $config_hash_after"
echo "Users preserved: $users_after"
echo "Backup: $backup_dir"

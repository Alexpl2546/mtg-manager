#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $# -ne 4 ]]; then
  echo "ERROR=invalid_arguments"
  echo "USAGE=$0 <container_name> <workdir> <port> <domain>"
  exit 1
fi

CONTAINER_NAME="$1"
WORKDIR="$2"
PORT="$3"
DOMAIN="$4"

INTERNAL_PORT="3128"
IMAGE="nineseconds/mtg:2"
CONFIG_PATH="$WORKDIR/config.toml"

command -v docker >/dev/null 2>&1 || {
  echo "ERROR=docker_not_found"
  exit 1
}

command -v ss >/dev/null 2>&1 || {
  echo "ERROR=ss_not_found"
  exit 1
}

if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
  echo "ERROR=invalid_port"
  exit 1
fi

if (( PORT < 1 || PORT > 65535 )); then
  echo "ERROR=invalid_port_range"
  exit 1
fi

if ss -tuln | awk '{print $5}' | grep -Eq "(^|:)$PORT$"; then
  echo "ERROR=port_in_use"
  exit 1
fi

if docker ps -a --format '{{.Names}}' | grep -Fxq "$CONTAINER_NAME"; then
  echo "ERROR=container_exists"
  exit 1
fi

mkdir -p "$WORKDIR"

SECRET_HEX="$(docker run --rm "$IMAGE" generate-secret --hex "$DOMAIN" | tr -d '\r\n')"

cat > "$CONFIG_PATH" <<EOF
secret = "$SECRET_HEX"
bind-to = "0.0.0.0:${INTERNAL_PORT}"
EOF

docker run -d \
  --name "$CONTAINER_NAME" \
  --restart unless-stopped \
  -v "$CONFIG_PATH:/config.toml:ro" \
  -p "${PORT}:${INTERNAL_PORT}" \
  "$IMAGE" \
  run /config.toml >/dev/null

sleep 2

ACCESS="$(docker exec "$CONTAINER_NAME" /mtg access /config.toml)"
TG_URL="$(printf '%s\n' "$ACCESS" | grep '"tg_url"' | head -n1 | cut -d '"' -f4)"
TG_URL_FIXED="$(printf '%s' "$TG_URL" | sed "s/port=${INTERNAL_PORT}/port=${PORT}/")"

if [[ -z "$TG_URL_FIXED" ]]; then
  echo "ERROR=failed_to_get_tg_url"
  docker logs "$CONTAINER_NAME" || true
  exit 1
fi

echo "STATUS=OK"
echo "TG_URL=$TG_URL_FIXED"
echo "PORT=$PORT"
echo "CONTAINER=$CONTAINER_NAME"
echo "WORKDIR=$WORKDIR"
echo "DOMAIN=$DOMAIN"

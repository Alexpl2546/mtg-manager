#!/usr/bin/env bash
set -Eeuo pipefail

if [ "$#" -ne 4 ]; then
  echo "Usage: $0 <container_name> <workdir> <port> <domain>" >&2
  exit 1
fi

CONTAINER_NAME="$1"
WORKDIR="$2"
PORT="$3"
DOMAIN="$4"

mkdir -p "$WORKDIR"

SECRET_HEX="$(docker run --rm nineseconds/mtg:2 generate-secret --hex "$DOMAIN")"

cat > "$WORKDIR/config.toml" <<EOF
secret = "$SECRET_HEX"
bind-to = "0.0.0.0:3128"
EOF

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

docker run -d \
  --name "$CONTAINER_NAME" \
  --restart unless-stopped \
  -v "$WORKDIR/config.toml:/config.toml:ro" \
  -p "${PORT}:3128/tcp" \
  nineseconds/mtg:2 \
  run /config.toml >/dev/null

ACCESS_JSON="$(docker exec "$CONTAINER_NAME" /mtg access /config.toml)"

TG_URL="$(printf '%s' "$ACCESS_JSON" | python3 -c '
import sys, json
data = json.load(sys.stdin)
print(data["ipv4"]["tg_url"])
')"

# заменяем порт 3128 на внешний
TG_URL="$(echo "$TG_URL" | sed "s/port=3128/port=${PORT}/")"

echo "STATUS=OK"
echo "CONTAINER=$CONTAINER_NAME"
echo "WORKDIR=$WORKDIR"
echo "PORT=$PORT"
echo "DOMAIN=$DOMAIN"
echo "TG_URL=$TG_URL"

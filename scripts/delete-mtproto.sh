#!/usr/bin/env bash
set -Eeuo pipefail

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <container_name> <workdir>" >&2
  exit 1
fi

CONTAINER_NAME="$1"
WORKDIR="$2"

# Останавливаем и удаляем контейнер
docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

# Удаляем рабочую директорию клиента
if [ -d "$WORKDIR" ]; then
  rm -rf "$WORKDIR"
fi

echo "STATUS=OK"
echo "CONTAINER=$CONTAINER_NAME"
echo "WORKDIR=$WORKDIR"

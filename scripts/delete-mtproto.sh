#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $# -ne 2 ]]; then
  echo "ERROR=invalid_arguments"
  echo "USAGE=$0 <container_name> <workdir>"
  exit 1
fi

CONTAINER_NAME="$1"
WORKDIR="$2"

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
rm -rf "$WORKDIR"

echo "STATUS=OK"
echo "CONTAINER=$CONTAINER_NAME"
echo "WORKDIR=$WORKDIR"

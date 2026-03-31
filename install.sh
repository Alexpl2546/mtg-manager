#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="/opt/mtg-bot"
SERVICE_PATH="/etc/systemd/system/mtg-bot.service"
PYTHON_BIN="/usr/bin/python3"
VENV_DIR="$APP_DIR/venv"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

require_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    echo "Запусти install.sh от root: sudo bash install.sh"
    exit 1
  fi
}

install_packages() {
  export DEBIAN_FRONTEND=noninteractive
  apt update
  apt install -y python3 python3-pip python3-venv docker.io curl ca-certificates
}

prepare_dirs() {
  mkdir -p "$APP_DIR"
  mkdir -p /opt/mtg-manager/users /opt/mtg-manager/configs
}

copy_files() {
  install -m 0755 "$REPO_DIR/mtg_bot.py" "$APP_DIR/mtg_bot.py"
  install -m 0644 "$REPO_DIR/mtg-bot.service" "$SERVICE_PATH"
  if [[ ! -f "$APP_DIR/.env" ]]; then
    install -m 0644 "$REPO_DIR/.env.example" "$APP_DIR/.env"
    echo "Создан файл $APP_DIR/.env из шаблона .env.example"
    echo "Отредактируй его перед запуском сервиса."
  fi
}

setup_venv() {
  if [[ ! -d "$VENV_DIR" ]]; then
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  fi
  "$VENV_DIR/bin/pip" install --upgrade pip
  "$VENV_DIR/bin/pip" install -r "$REPO_DIR/requirements.txt"
}

enable_docker() {
  systemctl enable --now docker
}

reload_service() {
  systemctl daemon-reload
  systemctl enable mtg-bot
}

start_service() {
  if grep -q '^BOT_TOKEN=$' "$APP_DIR/.env" || grep -q '^ALLOWED_USER_IDS=$' "$APP_DIR/.env"; then
    echo
    echo "Заполни $APP_DIR/.env и потом выполни:"
    echo "systemctl restart mtg-bot"
    exit 0
  fi

  systemctl restart mtg-bot
  systemctl status mtg-bot --no-pager -l || true
}

require_root
install_packages
prepare_dirs
copy_files
setup_venv
enable_docker
reload_service
start_service

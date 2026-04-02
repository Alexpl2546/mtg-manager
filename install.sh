#!/usr/bin/env bash
set -e

REPO_URL="https://github.com/Alexpl2546/mtg-manager"
INSTALL_DIR="/opt/mtg-bot"

echo "===> Обновление пакетов"
apt update -y

echo "===> Установка зависимостей"
apt install -y git python3 python3-venv python3-pip docker.io curl

echo "===> Запуск Docker"
systemctl enable docker
systemctl start docker

echo "===> Клонирование проекта"
rm -rf $INSTALL_DIR
git clone $REPO_URL $INSTALL_DIR

cd $INSTALL_DIR

echo "===> Создание venv"
python3 -m venv venv
source venv/bin/activate

echo "===> Установка Python зависимостей"
pip install -r requirements.txt

echo "===> Подготовка конфигов"
mkdir -p data

cp data/clients.json.example data/clients.json || true
cp data/settings.json.example data/settings.json || true

echo "===> Введи токен бота:"
read -r TOKEN

echo "$TOKEN" > .env

echo "===> Права на скрипты"
chmod +x scripts/*.sh

echo "===> Создание systemd сервиса"
cat > /etc/systemd/system/mtg-bot.service <<EOF
[Unit]
Description=MTProto Telegram Bot
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/bot.py
Restart=always
RestartSec=3
User=root

[Install]
WantedBy=multi-user.target
EOF

echo "===> Запуск сервиса"
systemctl daemon-reload
systemctl enable mtg-bot
systemctl start mtg-bot

echo "===> Готово"
systemctl status mtg-bot --no-pager

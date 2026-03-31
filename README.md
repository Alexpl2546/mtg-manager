# MTG Manager Bot

Telegram-бот для управления MTProto-пользователями через Docker.

## Что умеет

- создавать пользователя через `/add`
- показывать пользователей через `/users`
- показывать ссылку через `/link <user>`
- удалять пользователя через `/delete <user>`
- показывать логи через `/logs <user>`
- показывать занятые порты через `/ports`

## Быстрый старт

```bash
apt update && apt install -y git
git clone <YOUR_REPO_URL>
cd mtg-manager-repo
sudo bash install.sh
```

После первого запуска скрипт создаст `/opt/mtg-bot/.env`.

Открой его и заполни:

```bash
sudo nano /opt/mtg-bot/.env
```

Пример:

```env
BOT_TOKEN=123456:ABCDEF...
ALLOWED_USER_IDS=123456789
SERVER_ADDR_DEFAULT=1.2.3.4
DEFAULT_FAKE_TLS_HOST=ajax.googleapis.com
```

Потом:

```bash
sudo systemctl restart mtg-bot
sudo systemctl status mtg-bot --no-pager -l
```

## Полезные команды

```bash
sudo journalctl -u mtg-bot -f
sudo systemctl restart mtg-bot
sudo systemctl status mtg-bot --no-pager -l
```

## Где хранятся данные

- код бота: `/opt/mtg-bot`
- env-файл: `/opt/mtg-bot/.env`
- пользователи: `/opt/mtg-manager/users`
- конфиги mtg: `/opt/mtg-manager/configs`

## Обновление из репозитория

```bash
git pull
sudo bash install.sh
```

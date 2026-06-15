# Proxy Manager

Telegram-бот для управления Telemt, HTTP и SOCKS5-прокси.

## Безопасность

- Доступ разрешён только Telegram ID из `ADMIN_IDS`.
- Токены, клиентские базы и прокси-секреты не хранятся в Git.
- Рабочие JSON-файлы записываются атомарно.
- Сервису необходим ограниченный доступ к systemd, Telemt и 3proxy.

## Конфигурация

Создайте `/opt/proxy-manager/.env`:

```dotenv
BOT_TOKEN=telegram_bot_token
ADMIN_IDS=301615601
```

Несколько администраторов указываются через запятую.

Создайте рабочие настройки:

```bash
cp data/settings.json.example data/settings.json
```

Поля `http.host` и `socks5.host` должны содержать публичный адрес сервера.

## Запуск

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
set -a
source .env
set +a
venv/bin/python bot.py
```

Для production используйте systemd и отдельного системного пользователя.

## Telemt

Менеджер использует официальный Telemt Control API. Создание и удаление
пользователей выполняется атомарно и не требует перезапуска Telemt.

Не изменяйте `censorship.tls_domain` на работающей установке: существующие
Fake TLS ссылки используют старый домен и перестанут подключаться.

Безопасное обновление Telemt:

```bash
sudo bash scripts/audit-telemt.sh
sudo bash scripts/upgrade-telemt.sh 3.4.18
sudo bash scripts/harden-telemt.sh
```

Скрипт обновления проверяет SHA-256 официального релиза, сохраняет бинарник,
конфигурацию и unit-файл в `/var/backups/telemt/`, проверяет readiness и
автоматически откатывается при ошибке.

Скрипт hardening добавляет рекомендованные upstream capabilities
`CAP_NET_ADMIN` и `CAP_NET_BIND_SERVICE`, включает `NoNewPrivileges` и
устанавливает `show_link = []`, чтобы действующие ссылки не попадали в journald.

## Данные

Рабочие файлы создаются в `data/`:

- `telemt_clients.json`
- `http_clients.json`
- `socks5_clients.json`
- `settings.json`

Эти файлы могут содержать пароли и действующие ссылки доступа. Не добавляйте их
в Git, включая приватные репозитории.

## Тесты

```bash
pip install -r requirements-dev.txt
pytest
```

## Развёртывание

Архив релиза не должен содержать `.env` или рабочие `data/*.json`.

```bash
sudo bash scripts/deploy-proxy-manager.sh /tmp/proxy-manager-release.tar.gz
```

Перед заменой файлов скрипт проверяет JSON, создаёт backup в
`/var/backups/proxy-manager/`, устанавливает зависимости в `venv`, проверяет
Telemt API и автоматически откатывает проект при ошибке запуска.

Сверка локальной базы с Telemt ничего не изменяет:

```bash
set -a
source /opt/proxy-manager/.env
set +a
python3 scripts/reconcile-telemt.py
```

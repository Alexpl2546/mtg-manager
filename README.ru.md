# Proxy Manager

Telegram-бот и набор операционных инструментов для управления MTG/MTProto,
Telemt, HTTP- и SOCKS5-прокси на одном Linux-сервере.

English version: [README.en.md](README.en.md)

## Назначение репозитория

Это публичный репозиторий приложения. Он содержит исходный код, тесты,
безопасные примеры конфигурации и скрипты эксплуатации. Здесь не должно быть
production-секретов, реальных клиентских баз, VPS-аудитов, backup-архивов или
действующих ссылок подключения.

Связанный приватный репозиторий `mtg-manager-infrastructure` хранит Ansible-
конфигурацию окружения и только зашифрованные SOPS-секреты. Runtime-данные
клиентов не следует коммитить даже туда.

## Возможности

- Доступ к боту только для Telegram ID из `ADMIN_IDS`.
- Создание, просмотр и удаление клиентов MTG, Telemt, HTTP и SOCKS5.
- Выбор Fake TLS-домена для MTG и Telemt.
- Выделение свободных портов для отдельных MTG-контейнеров.
- Синхронизация пользователей HTTP/SOCKS5 с общей конфигурацией 3proxy.
- Работа с Telemt через официальный Control API без перезапуска при каждом
  изменении пользователя.
- Атомарная запись локальных JSON-индексов.
- Backup, health check и автоматический rollback при production-деплое.
- Аудит, hardening и проверяемое обновление Telemt.

## Архитектура

```text
Telegram administrator
        |
        v
     bot.py
        |
        +-- MTGProvider ------> Docker + /opt/mtg-clients/
        +-- TelemtProvider ---> Telemt Control API
        +-- HTTPProvider -----+
        +-- SOCKS5Provider ---+-> 3proxy configuration
        |
        +-- data/*.json (локальный индекс и настройки)
```

`bot.py` отвечает за Telegram-интерфейс и передаёт операции соответствующему
provider. Providers управляют внешними сервисами и сохраняют локальные
метаданные через `utils/storage.py`.

Telemt является источником истины для своих пользователей. Локальный
`telemt_clients.json` нужен боту как индекс отображения. Скрипт reconciliation
только сравнивает оба источника и ничего не удаляет автоматически.

## Карта артефактов

### Корень

| Артефакт | Назначение |
| --- | --- |
| `bot.py` | Точка входа aiogram, handlers, выбор протокола, создание, просмотр, удаление клиентов и смена домена. |
| `config.py` | Загрузка `BOT_TOKEN`, `ADMIN_IDS` и настроек Telemt API из окружения. |
| `requirements.txt` | Production-зависимости Python. |
| `requirements-dev.txt` | Инструменты тестирования и lint. |
| `pyproject.toml` | Настройки Ruff и pytest. |
| `.env.example` | Безопасный шаблон переменных окружения. |
| `.gitignore` | Исключение секретов, runtime JSON, архивов, логов и локального окружения. |
| `.gitattributes` | Нормализация окончаний строк и атрибутов файлов. |
| `SECURITY.md` | Правила сообщения об уязвимостях и обращения с секретами. |
| `LICENSE` | Лицензия проекта. |

### `providers/`

| Артефакт | Назначение |
| --- | --- |
| `base.py` | Абстрактный интерфейс provider: create, delete, get, list и health. |
| `mtg_manager.py` | Создание MTG-конфигурации, запуск отдельного Docker-контейнера и удаление клиента. |
| `telemt_manager.py` | HTTP-клиент Telemt Control API, readiness, reconciliation и управление пользователями. |
| `http_manager.py` | Генерация учётных данных HTTP-прокси и обновление 3proxy. |
| `socks5_manager.py` | Генерация учётных данных SOCKS5 и обновление 3proxy. |
| `__init__.py` | Обозначает каталог как Python-пакет. |

### `utils/`

| Артефакт | Назначение |
| --- | --- |
| `auth.py` | Middleware, запрещающий доступ Telegram-пользователям вне `ADMIN_IDS`. |
| `keyboards.py` | Reply- и inline-клавиатуры интерфейса бота. |
| `ports.py` | Поиск свободного MTG-порта с учётом системных и зарезервированных портов. |
| `state.py` | Небольшое in-memory состояние диалога: выбранный протокол и действие. |
| `storage.py` | Чтение и атомарная замена JSON-файлов. |
| `threeproxy.py` | Сбор пользователей, генерация конфигурации и безопасная перезагрузка 3proxy. |
| `validation.py` | Нормализация и проверка имён клиентов. |

### `scripts/`

| Артефакт | Назначение |
| --- | --- |
| `deploy-proxy-manager.sh` | Транзакционный deploy релизного архива с проверкой JSON, backup, новым venv, health check и rollback. |
| `post-deploy-check.sh` | Состояние сервисов, конфигурации, клиентских индексов, Telemt reconciliation и свежих ошибок. |
| `backup-runtime.sh` | Root-only backup текущей конфигурации и runtime-данных. |
| `audit-telemt.sh` | Сбор безопасной диагностической информации о Telemt перед изменениями. |
| `upgrade-telemt.sh` | Загрузка официального релиза, проверка SHA-256, backup и rollback обновления Telemt. |
| `harden-telemt.sh` | Systemd hardening, необходимые capabilities и отключение вывода ссылок в journald. |
| `reconcile-telemt.py` | Read-only сравнение локального индекса с пользователями Telemt. |
| `import-telemt-missing.py` | Контролируемый импорт отсутствующих локальных метаданных из Telemt. |
| `install-mtproto.sh` | Установка MTG-клиента с отдельной конфигурацией и контейнером. |
| `delete-mtproto.sh` | Удаление MTG-контейнера и его файлов. |
| `archive-legacy-proxy.sh` | Архивация устаревшей proxy-установки перед миграцией. |

### `data/`

`settings.json.example` документирует безопасную форму runtime-настроек:
Fake TLS-домены, публичные host и порты HTTP/SOCKS5. Рабочая копия
`data/settings.json` игнорируется Git.

Во время работы создаются:

| Файл | Содержимое |
| --- | --- |
| `mtg_clients.json` | Метаданные MTG-клиентов и выделенные порты. |
| `telemt_clients.json` | Локальный индекс Telemt-пользователей и ссылок. |
| `http_clients.json` | Имена, логины и пароли HTTP-прокси. |
| `socks5_clients.json` | Имена, логины и пароли SOCKS5-прокси. |
| `settings.json` | Рабочие домены, адреса и порты. |

Все эти рабочие файлы могут содержать секреты и исключены из Git.

### `tests/` и CI

| Артефакт | Назначение |
| --- | --- |
| `test_config.py` | Разбор администраторов и обязательность конфигурации. |
| `test_storage.py` | Атомарная запись и чтение JSON. |
| `test_telemt.py` | Формы ответов Telemt и извлечение Fake TLS-ссылки. |
| `test_validation.py` | Нормализация и допустимость клиентских имён. |
| `.github/workflows/ci.yml` | Автоматический запуск тестов и Ruff в GitHub Actions. |

### Дополнительная документация

- `docs/ARCHITECTURE.md` — краткая модель владения данными.
- `docs/OPERATIONS.md` — health check, backup, логи и rollback.
- `SECURITY.md` — запрет публикации чувствительных данных.

## Владение данными

| Данные | Источник истины | Production-путь |
| --- | --- | --- |
| Токен бота и ID администраторов | Системный администратор | `/opt/proxy-manager/.env` |
| Локальные метаданные клиентов | Proxy Manager | `/opt/proxy-manager/data/*.json` |
| Пользователи и секреты Telemt | Telemt | `/etc/telemt/telemt.toml` |
| HTTP/SOCKS5 runtime | 3proxy | `/etc/3proxy/3proxy.cfg` |
| Конфигурация MTG-клиентов | MTG provider | `/opt/mtg-clients/<name>/` |
| Backup Proxy Manager | deploy script | `/var/backups/proxy-manager/<timestamp>/` |
| Backup Telemt | upgrade script | `/var/backups/telemt/<timestamp>/` |

## Локальная разработка

Требуется Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
cp data/settings.json.example data/settings.json
```

Заполните `.env`, не добавляя его в Git:

```dotenv
BOT_TOKEN=telegram_bot_token
ADMIN_IDS=123456789
TELEMT_API_URL=http://127.0.0.1:9091
TELEMT_API_AUTH=
```

Проверки:

```bash
python -m pytest -q
python -m ruff check .
```

Запуск:

```bash
set -a
source .env
set +a
python bot.py
```

Полноценные операции providers рассчитаны на Linux-хост с Docker, systemd,
Telemt и 3proxy. На обычной рабочей станции безопасно запускать тесты и lint.

## Production-деплой

Релизный архив создаётся из отслеживаемых публичных файлов и не должен
содержать `.env`, рабочие `data/*.json`, логи или backup.

```bash
sudo bash scripts/deploy-proxy-manager.sh \
  /tmp/proxy-manager-release.tar.gz
sudo bash /opt/proxy-manager/scripts/post-deploy-check.sh
```

Приватный инфраструктурный репозиторий автоматизирует загрузку проверенного
архива и запуск этих команд через Ansible.

## Правила безопасности

- Никогда не коммитьте `.env`, runtime JSON и конфигурацию действующих прокси.
- Не публикуйте server IP, клиентские имена, пароли и ссылки подключения.
- Backup и audit-артефакты могут содержать секреты; храните их зашифрованными.
- Не меняйте Telemt `secret` или `censorship.tls_domain` без миграции:
  существующие ссылки перестанут работать.
- Перед удалением пользователя при расхождении Telemt и локального индекса
  сначала выполните read-only reconciliation.

## Git-процесс

`main` — стабильная ветка. Разработка ведётся в отдельных ветках:

```bash
git switch main
git pull --ff-only origin main
git switch -c codex/<task>
python -m pytest -q
python -m ruff check .
git push -u origin codex/<task>
```

Merge в `main` и production-deploy выполняются после проверки изменений.

## Состояние на 15 июня 2026 года

- Публичный `main`: `9f66ba1` (`Modernize proxy manager architecture`).
- Production развёрнут из этого состояния.
- `proxy-manager`, `telemt` и `3proxy` были активны после deploy.
- Локальный индекс и Telemt совпадали: 17 пользователей из 17.
- Локально проходили 10 тестов и Ruff.

Числа пользователей и состояние production являются снимком, а не
конфигурацией, на которую должен полагаться код.

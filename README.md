# MTProto Proxy Bot

Telegram-бот для управления MTProto-прокси через Docker.

Проект предназначен для быстрого и удобного создания прокси для пользователей с полным управлением через интерфейс Telegram без ручной работы с сервером.

---

## 🚀 Основные возможности

- Создание MTProto-прокси через Telegram
- Автоматическое выделение свободных портов
- Хранение клиентов в локальной базе (JSON)
- Просмотр клиентов через кнопки
- Получение ссылки подключения в один клик
- Удаление клиентов с подтверждением
- Смена домена генерации секретов
- Автоматическое управление Docker-контейнерами

---

## 📁 Структура проекта

```
mtg-bot/
├── bot.py                     # основной код бота
├── requirements.txt          # зависимости Python
├── scripts/
│   ├── install-mtproto.sh    # создание прокси
│   └── delete-mtproto.sh     # удаление прокси
├── data/
│   ├── clients.json.example  # шаблон базы клиентов
│   └── settings.json.example # шаблон настроек
├── .gitignore
└── README.md
```

---

## ⚙️ Требования

Перед началом убедись, что у тебя есть:

- Linux сервер (Ubuntu / Debian)
- Python 3.10+
- Docker установлен и запущен
- Открытые порты на сервере

---

## 📦 Установка

### 1. Клонирование

```bash
git clone <YOUR_REPOSITORY_URL>
cd mtg-bot
```

---

### 2. Виртуальное окружение

```bash
python3 -m venv venv
source venv/bin/activate
```

---

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

---

## 🔐 Настройка (ВАЖНО)

В проекте есть файлы, которые не хранятся в Git по соображениям безопасности.

---

### 1. `.env` — токен Telegram-бота

Создай файл:

```bash
nano .env
```

Добавь туда:

```
<TELEGRAM_BOT_TOKEN>
```

Пример:

```
123456789:AAExampleToken
```

📌 Получить токен можно через BotFather в Telegram.

---

### 2. `data/clients.json` — база клиентов

Создаётся из шаблона:

```bash
cp data/clients.json.example data/clients.json
```

Содержимое:

```json
{}
```

📌 Особенности:
- файл автоматически заполняется ботом
- содержит все созданные прокси
- не должен попадать в Git

---

### 3. `data/settings.json` — настройки домена

Создание:

```bash
cp data/settings.json.example data/settings.json
```

Пример:

```json
{
  "domain": "ajax.googleapis.com"
}
```

📌 Особенности:
- если файл отсутствует — создаётся автоматически
- используется для генерации новых прокси
- можно менять через бота

---

## ▶️ Запуск

```bash
python bot.py
```

---

## 🔁 Запуск как сервис (systemd)

Создай сервис:

```bash
nano /etc/systemd/system/mtg-bot.service
```

Содержимое:

```ini
[Unit]
Description=MTProto Telegram Bot
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/opt/mtg-bot
ExecStart=/opt/mtg-bot/venv/bin/python /opt/mtg-bot/bot.py
Restart=always
RestartSec=3
User=root

[Install]
WantedBy=multi-user.target
```

Запуск:

```bash
systemctl daemon-reload
systemctl enable mtg-bot
systemctl start mtg-bot
```

Проверка:

```bash
systemctl status mtg-bot
```

---

## 🧠 Как это работает

1. Ты создаёшь клиента через Telegram
2. Бот:
   - генерирует порт
   - создаёт Docker-контейнер
   - генерирует MTProto-секрет
3. Сохраняет данные в `clients.json`
4. Отдаёт готовую ссылку подключения

---

## ⚠️ Безопасность

Не добавляй в Git:

- `.env`
- `data/clients.json`

Они уже исключены через `.gitignore`.

---

## ⚡ Быстрый старт

```bash
cp data/clients.json.example data/clients.json
cp data/settings.json.example data/settings.json
nano .env
python bot.py
```

---

## 📌 Примечания

- имена клиентов автоматически приводятся к нижнему регистру
- разрешены только символы: `a-z`, `0-9`, `_`, `-`
- каждый клиент = отдельный Docker-контейнер
- порты не пересекаются

---

## 📈 Возможные улучшения

- автоматический деплой одной командой
- мониторинг контейнеров
- резервное копирование
- web-интерфейс

---

## 🧾 Лицензия

Используется в образовательных и практических целях.

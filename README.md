# MTProto Proxy Bot

Telegram-бот для управления MTProto-прокси через Docker.

Позволяет создавать, удалять и управлять прокси полностью через интерфейс Telegram.

---

## 📌 Возможности

- создание MTProto-прокси для клиентов  
- просмотр клиентов через кнопки  
- удаление клиентов с подтверждением  
- смена домена для генерации секретов  
- автоматическое управление контейнерами Docker  
- хранение данных клиентов в JSON  

---

## 📁 Структура проекта

mtg-bot/
├── bot.py
├── requirements.txt
├── scripts/
│   ├── install-mtproto.sh
│   └── delete-mtproto.sh
├── data/
│   ├── clients.json.example
│   └── settings.json.example
├── .gitignore
└── README.md

---

## ⚙️ Установка

git clone <your-repo-url>
cd mtg-bot

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

---

## 🔧 Подготовка конфигурационных файлов

### .env

Создай файл:

nano .env

Добавь:

<TELEGRAM_BOT_TOKEN>

---

### data/clients.json

cp data/clients.json.example data/clients.json

---

### data/settings.json

cp data/settings.json.example data/settings.json

---

## 🚀 Запуск

python bot.py

# MTProto Proxy Bot

Telegram-бот для управления MTProto-прокси через Docker.

## Возможности

- создание прокси для клиентов;
- просмотр клиентов через кнопки;
- удаление клиентов с подтверждением;
- смена домена для генерации новых секретов;
- хранение данных клиентов в JSON.

## Структура

- `bot.py` — основной код бота;
- `scripts/install-mtproto.sh` — создание прокси;
- `scripts/delete-mtproto.sh` — удаление прокси;
- `data/clients.json` — база клиентов;
- `data/settings.json` — настройки домена;
- `.env` — токен Telegram-бота.

## Установка

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp data/clients.json.example data/clients.json
cp data/settings.json.example data/settings.json
```

Создай `.env` с токеном бота одной строкой.

## Запуск

```bash
python bot.py
```

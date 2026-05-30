# Бот-анализатор речи

Telegram-бот, который анализирует голосовые сообщения и помогает следить за качеством речи.

## Что умеет

- **Слова-паразиты** — GPT находит паразиты в транскрипте и выделяет каждое вхождение жирным
- **Длинные паузы** — считает паузы ≥ 0.7 с: частоту (в минуту) и среднюю длительность
- **Темп речи** — слов в минуту
- **Прогресс** — после нескольких записей сравнивает текущий результат с твоим средним уровнем

## Стек

| | |
|---|---|
| Python 3.12 + [aiogram 3](https://aiogram.dev/) | Telegram Bot API |
| [gen-api.ru](https://gen-api.ru/) | Транскрипция (Whisper) и анализ паразитов (GPT) |
| SQLite + aiosqlite | Хранение результатов |
| [Caddy](https://caddyserver.com/) | HTTPS-прокси для webhook |
| Docker Compose | Развёртывание |

## Быстрый старт

```bash
git clone https://github.com/yourname/lang_estimation_bot
cd lang_estimation_bot
cp .env.example .env   # заполни токены
docker compose up -d
```

## Переменные окружения

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен бота от [@BotFather](https://t.me/BotFather) |
| `GEN_API_TOKEN` | API-ключ [gen-api.ru](https://gen-api.ru/) |
| `WEBHOOK_HOST` | Публичный URL сервера, например `https://your.domain` |
| `WEB_PORT` | Порт внутри контейнера (по умолчанию `8080`) |

В `Caddyfile` замени домен на свой.

## Ограничения

- Длина аудио: 10–60 секунд
- Лимит: 5 записей в день на пользователя

## Структура проекта

```
bot/
├── main.py         запуск бота, webhook
├── handlers.py     обработчики сообщений, вычисление метрик
├── db.py           работа с БД (aiosqlite / SQLite)
├── Dockerfile
└── tests/          юнит-тесты (pytest)
docker-compose.yml
Caddyfile
.env.example
```

## Запуск тестов

```bash
cd bot
pip install -r requirements-test.txt
pytest tests/
```
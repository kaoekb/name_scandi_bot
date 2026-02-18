# name_scandi_bot

Telegram-бот, который в шуточной форме «доказывает», что любое имя имеет скандинавские корни.

- Бот: [@name_scandi_bot](https://t.me/name_scandi_bot)
- Смежные боты из меню миров: [@name_slavic_bot](https://t.me/name_slavic_bot), [@name_kelt_bot](https://t.me/name_kelt_bot)

## Что умеет

- Принимает любое имя от пользователя.
- Отправляет запрос в OpenAI и генерирует харизматичный, мифологический ответ.
- Показывает меню «миров» с переходом в другие тематические боты.
- Логирует события в `logs/bot.log`.
- Отправляет уведомления админу при ошибках.

## Стек

- Python 3.11
- `pyTelegramBotAPI` (Telegram Bot API)
- OpenAI Python SDK (`openai>=1.0.0`)
- Docker + Docker Compose
- GitLab CI/CD (сборка и деплой через `.gitlab-ci.yml`)

## Переменные окружения

Скопируйте шаблон и заполните значения:

```bash
cp .env.example .env
```

Файл `.env`:

```env
TOKEN_TG=your_telegram_bot_token
OPENAI_KEY=your_openai_api_key
ADMIN_ID=your_telegram_user_id
```

- `TOKEN_TG` — токен Telegram-бота (обязательно).
- `OPENAI_KEY` — API-ключ OpenAI (обязательно).
- `ADMIN_ID` — Telegram ID администратора для уведомлений об ошибках (опционально, но рекомендуется).

Если `TOKEN_TG` или `OPENAI_KEY` не заданы, бот завершит работу при старте.

## Локальный запуск (без Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Запуск через Docker Compose

```bash
docker-compose up -d --build
```

Остановка:

```bash
docker-compose down
```

Логи:

```bash
docker-compose logs -f
```

## CI/CD (GitLab)

Pipeline в `.gitlab-ci.yml` включает три стадии:

1. `cleanup` — очистка старых Docker-образов.
2. `build` — сборка образа `name_scandi_bot`.
3. `deploy` — перезапуск сервиса через `docker-compose up -d --build`.

Деплой выполняется для ветки `main`.

## Структура проекта

```text
.
├── main.py                # Точка входа Telegram-бота
├── bot/
│   ├── responder.py       # Работа с OpenAI и генерация ответа
│   └── notifier.py        # Уведомления админу о сбоях
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── requirements.txt
└── .gitlab-ci.yml
```

## Как это работает

1. Пользователь отправляет имя.
2. Бот формирует prompt вида: «Шуточно докажи, что имя X — скандинавское».
3. Ответ генерируется моделью OpenAI (сейчас в коде используется `gpt-3.5-turbo`).
4. Готовый текст отправляется пользователю в Telegram.

## Типовые проблемы

- `❌ Переменные окружения не заданы`  
  Проверьте `.env` и наличие `TOKEN_TG`, `OPENAI_KEY`.

- Бот не отвечает  
  Проверьте логи: `logs/bot.log` или `docker-compose logs -f`.

- Ошибки OpenAI API  
  Проверьте валидность `OPENAI_KEY` и доступность API.

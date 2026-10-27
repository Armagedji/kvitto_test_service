# Kvitto test assignment — Payments Service

Тестовое задание для Kvitto: сервис приёма оплаты курса онлайн-школы на
FastAPI. Поддерживает тарифы, промокоды, графики рассрочки, идемпотентное
создание платежей и вебхуки банка с HMAC-подписью.

## Стек

- Python 3.12, FastAPI, Pydantic v2
- PostgreSQL 16, SQLAlchemy 2 (async, asyncpg), Alembic (синхронные миграции через psycopg)
- pytest + httpx (ASGITransport), ruff
- Docker, docker compose, GitHub Actions

## Запуск через Docker

    cp .env.example .env
    docker compose up --build

Приложение доступно на http://localhost:8000, OpenAPI — на
http://localhost:8000/docs. Миграции (alembic upgrade head) накатываются
автоматически при старте контейнера.

Остановка:

    docker compose down        # сохранить данные
    docker compose down -v     # удалить данные

## Локальный запуск (без Docker)

Нужен запущенный PostgreSQL на localhost:5432 с пользователем, паролем и
базой payments.

    python -m venv .venv
    source .venv/bin/activate          # Windows: .venv\Scripts\activate
    pip install -e ".[dev]"
    cp .env.example .env
    alembic upgrade head
    uvicorn app.main:app --reload

## Тесты

    pytest -q

Тесты гоняются против реального PostgreSQL (тот же DATABASE_URL из .env) и
очищают таблицу payments между тестами. Перед запуском нужно убедиться, что
миграции обновлены:

    alembic upgrade head

## Линт

    ruff check .
    ruff format --check .

## Примеры запросов curl

### Список тарифов

    curl -s http://localhost:8000/tariffs | python -m json.tool

Ответ:

    [
      {"id": 1, "title": "basic",    "price": 990000},
      {"id": 2, "title": "standard", "price": 1990000},
      {"id": 3, "title": "premium",  "price": 2990000}
    ]

Цены в копейках (целое число). 1990000 = 19 900 ₽.

### Создание платежа (карта, без промокода)

    curl -s -X POST http://localhost:8000/payments \
      -H "Content-Type: application/json" \
      -d '{"tariff_id":2,"email":"a@example.com","method":"card"}' \
      | python -m json.tool

### Создание платежа с промокодом (регистр не важен)

    curl -s -X POST http://localhost:8000/payments \
      -H "Content-Type: application/json" \
      -d '{"tariff_id":2,"email":"a@example.com","method":"sbp","promo_code":"kvitto10"}' \
      | python -m json.tool

discount = 199000, amount = 1791000.

### Создание платежа с рассрочкой (3 месяца)

    curl -s -X POST http://localhost:8000/payments \
      -H "Content-Type: application/json" \
      -d '{"tariff_id":2,"email":"a@example.com","method":"installment","installment_months":3}' \
      | python -m json.tool

schedule = [663334, 663333, 663333], sum(schedule) == amount.

### Идемпотентное создание (повтор с тем же Idempotency-Key -> 200, тот же id)

    curl -s -X POST http://localhost:8000/payments \
      -H "Content-Type: application/json" \
      -H "Idempotency-Key: demo-key-1" \
      -d '{"tariff_id":2,"email":"a@example.com","method":"card"}'
    # 201

    curl -s -X POST http://localhost:8000/payments \
      -H "Content-Type: application/json" \
      -H "Idempotency-Key: demo-key-1" \
      -d '{"tariff_id":2,"email":"a@example.com","method":"card"}'
    # 200, тот же id

### Чтение платежей

    curl -s "http://localhost:8000/payments?email=a@example.com&status=pending" \
      | python -m json.tool

### Вебхук банка (HMAC-SHA256 по сырому телу запроса)

    PID=<id платежа>
    RAW="{\"payment_id\":\"$PID\",\"status\":\"succeeded\"}"
    SIG=$(printf '%s' "$RAW" | openssl dgst -sha256 -hmac "dev-secret" -hex | awk '{print $NF}' | tr -d '\r\n')

    curl -s -X POST http://localhost:8000/webhooks/bank \
      -H "Content-Type: application/json" \
      -H "X-Signature: $SIG" \
      --data-binary "$RAW"
    # {"result":"ok"}

Неверная подпись -> 401. Несуществующий платёж -> 404. Запрещённый
переход -> 409 с телом {"error":"invalid_transition"} (статус не
меняется).

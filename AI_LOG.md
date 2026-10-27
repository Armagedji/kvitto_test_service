# AI_LOG

В этом файле описано, какие AI-инструменты и модели использовались при
разработке тестового задания, как ставились задачи, а также где модель
ошибалась или давала слабое решение.

## Инструменты и модели

- DeepSeek — основной ассистент по архитектуре, генерации кода и отладке
- Весь сгенерированный код проверялся, запускался локально и
  корректировался перед коммитом.

## Ключевые запросы

### 1. Первый запрос с полным контекстом для модели

```
Я делаю сервис на Python, через который онлайн-школа принимает оплату курса. Это тестовое задание, аутентификация в проекте не нужна.
Стек: FastAPI + Pydantic v2, Python 3.12, PostgreSQL, pytest, httpx, Alembic, Docker.
Также для Github Actions использоваться ruff

Предметная область:
Тарифы: создаются при старте: basic — 9 900 ₽, standard — 19 900 ₽, premium — 29 900 ₽. Это seed-данные, создающиеся через Alembic-миграцию
Деньги: все суммы в API и в базе — в копейках, целым числом: 19 900 ₽ → 1990000 . Никаких float .
Промокод: KVITTO10 даёт −10% от цены тарифа, регистр не важен. Неизвестный код — ошибка 422.
Способ оплаты: card , sbp или installment . Для рассрочки обязателен installment_months : 3, 6 или 12.
График рассрочки: сумма к оплате делится на срок в копейках. Сумма всех платежей графика ровно равна сумме к оплате; лишние копейки — в первые платежи. Даты платежей не нужны.
Статусы: новый платёж — pending . Допустимые переходы: pending → succeeded , pending → failed , succeeded → refunded . Остальные запрещены.

Пример: standard без промокода, рассрочка на 3 месяца
amount = 1990000
schedule = [663334, 663333, 663333]
 (в сумме ровно 1990000)

Эндпоинты, которые будут созданы после:
GET /tariffs: 200 — список тарифов [{ id, title, price }] .
POST /payments: Тело: tariff_id , email , method , installment_months (для рассрочки), promo_code (необязательно). 201 — платёж создан. Если передан заголовок Idempotency-Key и платёж с таким ключом уже есть — вернуть его же с кодом 200, второй не создавать.
GET /payments/{id}: 200 — платёж; 404, если его нет.
GET /payments:  Фильтры по email и status
POST /webhooks/bank: Банк сообщает о смене статуса. Тело: payment_id , status . Платежа нет — 404. Запрещённый переход — 409 { error: "invalid_transition" } , статус не меняется. Успех — 200 { result: "ok" } .
Платёж в ответах: id , status , tariff_id , amount , discount , method , installment_months , schedule — список сумм в копейках или null , email , created_at . Ошибки валидации — стандартный ответ FastAPI с кодом 422, свой формат не нужен.


В проекте нужно будет реализовать миграцию Alembic, docker compose, проверку подписи вебхука (заголовок X-Signature — HMAC-SHA256 от тела запроса с секретом
из переменной WEBHOOK_SECRET , неверная подпись — 401), Github Actions (ruff + pytest для push).
```

### 2. Разбор падения pytest / asyncpg по event loop

Контекст: полный трейс pytest — десятки
`AttributeError: 'NoneType' object has no attribute 'send'` и
`RuntimeError: Event loop is closed` из asyncpg / ProactorEventLoop на
Windows, 12 failed / 19 passed.

Запрос:
`Я получаю большое количество ошибок в тестах. Проанализируй прикрепленный файл
и выясни причину ошибок. После напиши варианты исправления.`

Результат: подмена
app.db.engine в conftest.py. Исправление сработало с первого раза.

## Где модель ошибалась или давала слабое решение

### 1. Deprecated константа

Из-за устаревшей информации у модели возвращалась Deprecated константа:
`status_code=status.HTTP_422_UNPROCESSABLE_ENTITY`.

Увидев предупреждение в терминале Python, я изменил константу на поддерживаемую:
`status_code=status.HTTP_422_UNPROCESSABLE_CONTENT`

### 2. `raise HTTPException(...)` без `from` в `except` (ruff B904)

Модель сгенерировала обработчики исключений в роутерах без использования `from`:

    except payments_service.PromoCodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        )

Используя `ruff check .`, я увидел нарушение правила ruff B904:

    B904 Within an `except` clause, raise exceptions with `raise ... from err`
    or `raise ... from None` to distinguish them from errors in exception handling

Явный `from exc` сохраняет `__cause__` и делает цепочку исключений
читаемой.

Исправлено добавлением `from exc` к каждому `raise`:

    except payments_service.PromoCodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

После правки `ruff check .` по этим строкам стал чистым.

### 3. Отсутствующий тест на рассрочку 12 месяцев

В ТЗ явно требуется проверять, что сумма графика равна сумме к оплате
для 3, 6 и 12 месяцев. Модель сгенерировала тесты только для 3 месяцев
(пример из ТЗ) и 6 месяцев (с промокодом).

Я заметил это, сверяя требования из ТЗ с содержимым `tests/test_payments.py`.

Исправлено добавлением параметризованного теста `test_installment_schedule_sums_to_amount`.

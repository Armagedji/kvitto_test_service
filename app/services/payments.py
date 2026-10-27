from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models import Payment, PaymentStatus, Tariff
from app.schemas import PaymentCreate

import uuid

PROMO_KVITTO10 = "KVITTO10"
PROMO_DISCOUNT_PERCENT = 10


class PromoCodeError(ValueError):
    """Raised when a promo code is unknown. Maps to HTTP 422 at the router layer."""


class TariffNotFoundError(ValueError):
    """Raised when tariff_id does not exist. Maps to HTTP 422 at the router layer."""


def apply_promo_code(price: int, promo_code: str | None) -> tuple[int, int]:
    if promo_code is None:
        return 0, price

    code = promo_code.strip().upper()
    if not code:
        return 0, price

    if code != PROMO_KVITTO10:
        raise PromoCodeError(f"unknown promo code: {promo_code}")

    discount = price * PROMO_DISCOUNT_PERCENT // 100
    return discount, price - discount


def build_installment_schedule(amount: int, months: int) -> list[int]:
    base, remainder = divmod(amount, months)
    return [base + 1] * remainder + [base] * (months - remainder)


async def create_payment(
        session: AsyncSession,
        data: PaymentCreate,
        idempotency_key: str | None = None,
) -> tuple[Payment, bool]:

    if idempotency_key is not None:
        existing = await find_by_idempotency_key(session, idempotency_key)
        if existing is not None:
            return existing, False

    tariff = await session.get(Tariff, data.tariff_id)
    if tariff is None:
        raise TariffNotFoundError(f"tariff {data.tariff_id} not found")

    discount, amount = apply_promo_code(tariff.price, data.promo_code)

    schedule: list[int] | None = None
    if data.method == "installment":
        assert data.installment_months is not None
        schedule = build_installment_schedule(amount, data.installment_months)

    payment = Payment(
        id=uuid.uuid4(),
        status=PaymentStatus.pending.value,
        tariff_id=tariff.id,
        amount=amount,
        discount=discount,
        method=data.method,
        installment_months=data.installment_months,
        schedule=schedule,
        email=str(data.email),
        idempotency_key=idempotency_key,
    )
    session.add(payment)
    try:
        await session.commit()
    except IntegrityError:
        # Откат на случай проблемы с параллельными запросами
        await session.rollback()
        # На всякий случай проверка еще двух возможных ошибок
        if idempotency_key is None:
            raise
        existing = await find_by_idempotency_key(session, idempotency_key)
        if existing is None:
            raise
        return existing, False

    await session.refresh(payment)
    return payment, True


async def find_by_idempotency_key(session: AsyncSession, key: str) -> Payment | None:
    stmt = select(Payment).where(Payment.idempotency_key == key)
    return (await session.execute(stmt)).scalar_one_or_none()

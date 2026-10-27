from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Payment
from app.schemas import PaymentOut, PaymentStatus

router = APIRouter(tags=["payments"])


@router.get("/payments/{payment_id}", response_model=PaymentOut)
async def get_payment(
        payment_id: UUID,
        session: AsyncSession = Depends(get_session),
) -> Payment:
    payment = await session.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="payment not found")
    return payment


@router.get("/payments", response_model=list[PaymentOut])
async def list_payments(
        email: str | None = Query(default=None),
        status_filter: PaymentStatus | None = Query(default=None, alias="status"),
        session: AsyncSession = Depends(get_session),
) -> list[Payment]:
    stmt = select(Payment).order_by(Payment.created_at.desc())
    if email is not None:
        stmt = stmt.where(Payment.email == email)
    if status_filter is not None:
        stmt = stmt.where(Payment.status == status_filter)
    result = await session.execute(stmt)
    return list(result.scalars().all())

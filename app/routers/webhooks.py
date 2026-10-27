from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.models import Payment
from app.schemas import WebhookIn, WebhookOk
from app.services import webhook as webhook_service

router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/bank", response_model=WebhookOk)
async def bank_webhook(
    request: Request,
    x_signature: str | None = Header(default=None, alias="X-Signature"),
    session: AsyncSession = Depends(get_session),
) -> WebhookOk:
    raw_body = await request.body()

    if not webhook_service.verify_signature(raw_body, x_signature, settings.webhook_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid signature")

    try:
        payload = WebhookIn.model_validate_json(raw_body)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        )

    result = await session.execute(select(Payment).where(Payment.id == payload.payment_id))
    payment = result.scalar_one_or_none()
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="payment not found")

    if not webhook_service.is_transition_allowed(payment.status, payload.status):
        return JSONResponse(status_code=409, content={"error": "invalid_transition"}) # Кастомная ошибка

    payment.status = payload.status
    await session.commit()
    return WebhookOk()
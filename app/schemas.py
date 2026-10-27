from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

# ---------- Общие ----------

PaymentMethod = Literal["card", "sbp", "installment"]
PaymentStatus = Literal["pending", "succeeded", "failed", "refunded"]
InstallmentMonths = Literal[3, 6, 12]


# ---------- Tariffs ----------


class TariffOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    price: int  # копейки


# ---------- Payments: вход ----------


class PaymentCreate(BaseModel):
    tariff_id: int
    email: EmailStr
    method: PaymentMethod
    installment_months: InstallmentMonths | None = None
    promo_code: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def check_installment(self) -> "PaymentCreate":
        if self.method == "installment":
            if self.installment_months is None:
                raise ValueError("installment_months is required for installment method")
        else:
            if self.installment_months is not None:
                raise ValueError("installment_months is allowed only for installment method")
        return self


# ---------- Payments: выход ----------


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: PaymentStatus
    tariff_id: int
    amount: int
    discount: int
    method: PaymentMethod
    installment_months: int | None = None
    schedule: list[int] | None = None
    email: EmailStr
    created_at: datetime


# ---------- Webhook ----------


class WebhookIn(BaseModel):
    payment_id: UUID
    status: PaymentStatus


class WebhookOk(BaseModel):
    result: Literal["ok"] = "ok"

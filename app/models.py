import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    succeeded = "succeeded"
    failed = "failed"
    refunded = "refunded"


class PaymentMethod(str, enum.Enum):
    card = "card"
    sbp = "sbp"
    installment = "installment"


class Tariff(Base):
    __tablename__ = "tariffs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    price: Mapped[int] = mapped_column(BigInteger, nullable=False)  # копейки


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=PaymentStatus.pending.value
    )

    tariff_id: Mapped[int] = mapped_column(ForeignKey("tariffs.id"), nullable=False)

    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)

    discount: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    method: Mapped[str] = mapped_column(String(16), nullable=False)

    installment_months: Mapped[int | None] = mapped_column(Integer, nullable=True)

    schedule: Mapped[list[int] | None] = mapped_column(JSONB, nullable=True)

    email: Mapped[str] = mapped_column(String(254), nullable=False)

    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

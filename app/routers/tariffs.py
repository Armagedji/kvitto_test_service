from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Tariff
from app.schemas import TariffOut

router = APIRouter(tags=["tariffs"])


@router.get("/tariffs", response_model=list[TariffOut])
async def list_tariffs(session: AsyncSession = Depends(get_session)) -> list[Tariff]:
    result = await session.execute(select(Tariff).order_by(Tariff.id))
    return list(result.scalars().all())

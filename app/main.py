from fastapi import FastAPI

from app.config import settings
from app.routers import payments, tariffs

app = FastAPI(title="Payments Service", version="0.1.0")

app.include_router(payments.router)
app.include_router(tariffs.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/_debug/config")
async def debug_config() -> dict[str, str]:
    return {"webhook_secret_set": str(bool(settings.webhook_secret))}

from fastapi import FastAPI

from app.config import settings

app = FastAPI(title="Payments Service", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/_debug/config")
async def debug_config() -> dict[str, str]:
    return {"webhook_secret_set": str(bool(settings.webhook_secret))}
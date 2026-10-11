import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request

from app import db
from app.bot import bot, dp, refresh_and_deliver
from app.config import settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("radar")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db(settings.database_url)
    webhook_url = f"{settings.webhook_base_url.rstrip('/')}/webhook/{settings.webhook_secret}"
    await bot.set_webhook(webhook_url, drop_pending_updates=False)
    log.info("Webhook configured")
    yield
    await bot.session.close()
    await db.close()


app = FastAPI(title="Radar Bot", version="1.0.0", lifespan=lifespan)


@app.get("/")
async def root():
    return {"status": "ok", "service": "radar-bot", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/webhook/{secret}")
async def webhook(secret: str, request: Request):
    if secret != settings.webhook_secret:
        raise HTTPException(status_code=403, detail="Forbidden")
    from aiogram.types import Update
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}


@app.post("/internal/refresh")
async def refresh(x_cron_secret: str | None = Header(default=None)):
    if x_cron_secret != settings.cron_secret:
        raise HTTPException(status_code=403, detail="Forbidden")
    sent = await refresh_and_deliver()
    return {"ok": True, "sent": sent}

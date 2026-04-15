from fastapi import FastAPI
from contextlib import asynccontextmanager
from loguru import logger

import handlers # noqa, get handlers for Telegram
from routes import root_router
from settings import get_settings

cfg = get_settings()

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}

@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info("🚀 Starting application")
    from bot import start_telegram
    await start_telegram()
    yield
    logger.info("⛔ Stopping application")

app = FastAPI(lifespan=lifespan)
app.include_router(root_router)



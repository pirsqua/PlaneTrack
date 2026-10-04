"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from app.api.v1.routes import api_router
from app.config import get_settings
from app.services.pipeline import run_pipeline

logging.basicConfig()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logging.getLogger().setLevel(settings.log_level)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_pipeline,
        trigger="interval",
        seconds=settings.pipeline_interval_seconds,
        args=[settings],
        id="pipeline",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Pipeline scheduler started (interval=%ds)", settings.pipeline_interval_seconds)
    yield
    scheduler.shutdown(wait=False)
    logger.info("Pipeline scheduler stopped")


app = FastAPI(
    title="PlaneTracker",
    description="Live aircraft tracking via OpenSky Network with Bronze/Silver/Gold pipeline.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}

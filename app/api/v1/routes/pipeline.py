"""Pipeline management endpoints."""

import logging

from fastapi import APIRouter

from app.core.dependencies import SettingsDep
from app.models.gold import FlightStats
from app.services.pipeline import run_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ingest", response_model=FlightStats, status_code=202)
async def trigger_ingest(settings: SettingsDep) -> FlightStats:
    """Manually trigger a Bronze → Silver → Gold pipeline run."""
    logger.info("Manual pipeline ingest triggered")
    return await run_pipeline(settings)

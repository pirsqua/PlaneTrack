"""Aggregated statistics endpoints — reads from the Gold layer."""

import logging

from fastapi import APIRouter, HTTPException

from app.core.dependencies import SettingsDep
from app.models.gold import FlightStats
from app.storage.adls import ADLSClient

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=FlightStats)
async def get_stats(settings: SettingsDep) -> FlightStats:
    """Return flight statistics from the latest Gold snapshot."""
    storage = ADLSClient(settings)
    path = storage.latest_path("gold")
    if path is None:
        raise HTTPException(status_code=503, detail="No Gold data available yet — run the pipeline first.")
    df = storage.read_parquet(path)
    row = df.to_dict(orient="records")[0]
    return FlightStats.model_validate(row)

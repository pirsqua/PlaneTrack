"""Aircraft query endpoints — reads from the Silver layer."""

import logging

from fastapi import APIRouter, HTTPException

from app.core.dependencies import SettingsDep
from app.models.silver import AircraftState
from app.storage.adls import ADLSClient

logger = logging.getLogger(__name__)
router = APIRouter()


def _latest_silver(settings) -> list[AircraftState]:
    storage = ADLSClient(settings)
    path = storage.latest_path("silver")
    if path is None:
        raise HTTPException(status_code=503, detail="No Silver data available yet — run the pipeline first.")
    df = storage.read_parquet(path)
    return [AircraftState.model_validate(row) for row in df.to_dict(orient="records")]


@router.get("/", response_model=list[AircraftState])
async def list_aircraft(settings: SettingsDep) -> list[AircraftState]:
    """Return all tracked aircraft from the latest Silver snapshot."""
    return _latest_silver(settings)


@router.get("/{icao24}", response_model=AircraftState)
async def get_aircraft(icao24: str, settings: SettingsDep) -> AircraftState:
    """Return a single aircraft by ICAO24 address."""
    states = _latest_silver(settings)
    match = next((s for s in states if s.icao24 == icao24.lower()), None)
    if match is None:
        raise HTTPException(status_code=404, detail=f"Aircraft {icao24!r} not found in latest snapshot.")
    return match

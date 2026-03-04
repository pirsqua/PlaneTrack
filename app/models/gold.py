"""Aggregated analytics schemas — Gold layer."""

from datetime import datetime

from pydantic import BaseModel


class FlightStats(BaseModel):
    snapshot_time: datetime
    total_tracked: int
    total_airborne: int
    total_on_ground: int
    by_country: dict[str, int]

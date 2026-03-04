"""Cleaned and normalised aircraft state — Silver layer."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field, field_validator

from app.models.bronze import StateVector


class AircraftState(BaseModel):
    icao24: str
    callsign: str | None
    origin_country: str | None
    time_position: datetime | None
    last_contact: datetime | None
    longitude: float | None
    latitude: float | None
    baro_altitude_m: float | None
    geo_altitude_m: float | None
    on_ground: bool
    velocity_ms: float | None
    true_track_deg: float | None
    vertical_rate_ms: float | None
    squawk: str | None
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("callsign", mode="before")
    @classmethod
    def strip_callsign(cls, v: str | None) -> str | None:
        return v.strip() or None if v else None

    @classmethod
    def from_bronze(cls, sv: StateVector) -> "AircraftState | None":
        """Return None if ICAO24 is missing (unusable record)."""
        if not sv.icao24:
            return None

        def _ts(epoch: int | None) -> datetime | None:
            return datetime.fromtimestamp(epoch, tz=UTC) if epoch is not None else None

        return cls(
            icao24=sv.icao24,
            callsign=sv.callsign,
            origin_country=sv.origin_country,
            time_position=_ts(sv.time_position),
            last_contact=_ts(sv.last_contact),
            longitude=sv.longitude,
            latitude=sv.latitude,
            baro_altitude_m=sv.baro_altitude,
            geo_altitude_m=sv.geo_altitude,
            on_ground=sv.on_ground or False,
            velocity_ms=sv.velocity,
            true_track_deg=sv.true_track,
            vertical_rate_ms=sv.vertical_rate,
            squawk=sv.squawk,
        )

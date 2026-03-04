"""Raw OpenSky Network response schemas — no transformation, stored as-is."""

from pydantic import BaseModel


class StateVector(BaseModel):
    """Positional fields from the OpenSky /states/all response array."""

    icao24: str | None
    callsign: str | None
    origin_country: str | None
    time_position: int | None
    last_contact: int | None
    longitude: float | None
    latitude: float | None
    baro_altitude: float | None
    on_ground: bool | None
    velocity: float | None
    true_track: float | None
    vertical_rate: float | None
    sensors: list[int] | None
    geo_altitude: float | None
    squawk: str | None
    spi: bool | None
    position_source: int | None

    @classmethod
    def from_list(cls, row: list) -> "StateVector":
        """Parse from the raw positional array returned by OpenSky."""
        return cls(
            icao24=row[0],
            callsign=row[1],
            origin_country=row[2],
            time_position=row[3],
            last_contact=row[4],
            longitude=row[5],
            latitude=row[6],
            baro_altitude=row[7],
            on_ground=row[8],
            velocity=row[9],
            true_track=row[10],
            vertical_rate=row[11],
            sensors=row[12],
            geo_altitude=row[13],
            squawk=row[14],
            spi=row[15],
            position_source=row[16] if len(row) > 16 else None,
        )


class BronzeSnapshot(BaseModel):
    """A single OpenSky polling snapshot."""

    time: int
    states: list[StateVector]

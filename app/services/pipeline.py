"""Bronze → Silver → Gold pipeline orchestration."""

import logging
from collections import Counter
from datetime import UTC, datetime

import pandas as pd

from app.config import Settings
from app.models.bronze import BronzeSnapshot
from app.models.gold import FlightStats
from app.models.silver import AircraftState
from app.services.opensky import OpenSkyClient
from app.storage.adls import ADLSClient

logger = logging.getLogger(__name__)


def _partition_path(layer: str, snapshot_time: int, suffix: str = "") -> str:
    dt = datetime.fromtimestamp(snapshot_time, tz=UTC)
    base = f"{layer}/{dt:%Y/%m/%d/%H}/{snapshot_time}"
    return f"{base}{suffix}.parquet"


def _bronze_to_df(snapshot: BronzeSnapshot) -> pd.DataFrame:
    rows = [sv.model_dump() for sv in snapshot.states]
    df = pd.DataFrame(rows)
    df["snapshot_time"] = snapshot.time
    return df


def _silver_from_bronze(snapshot: BronzeSnapshot) -> list[AircraftState]:
    states = [AircraftState.from_bronze(sv) for sv in snapshot.states]
    return [s for s in states if s is not None]


def _silver_to_df(states: list[AircraftState]) -> pd.DataFrame:
    return pd.DataFrame([s.model_dump() for s in states])


def _aggregate_gold(states: list[AircraftState], snapshot_time: int) -> FlightStats:
    airborne = [s for s in states if not s.on_ground]
    on_ground = [s for s in states if s.on_ground]
    by_country = dict(Counter(s.origin_country for s in airborne if s.origin_country))
    return FlightStats(
        snapshot_time=datetime.fromtimestamp(snapshot_time, tz=UTC),
        total_tracked=len(states),
        total_airborne=len(airborne),
        total_on_ground=len(on_ground),
        by_country=by_country,
    )


async def run_pipeline(settings: Settings) -> FlightStats:
    """Execute a full Bronze → Silver → Gold ingestion cycle."""
    client = OpenSkyClient(settings)
    storage = ADLSClient(settings)

    # Bronze
    snapshot: BronzeSnapshot = await client.fetch_states()
    bronze_df = _bronze_to_df(snapshot)
    bronze_path = _partition_path("bronze", snapshot.time)
    storage.write_parquet(bronze_path, bronze_df)
    logger.info("Bronze written: %s (%d rows)", bronze_path, len(bronze_df))

    # Silver
    silver_states = _silver_from_bronze(snapshot)
    silver_df = _silver_to_df(silver_states)
    silver_path = _partition_path("silver", snapshot.time)
    storage.write_parquet(silver_path, silver_df)
    logger.info("Silver written: %s (%d rows)", silver_path, len(silver_df))

    # Gold
    stats = _aggregate_gold(silver_states, snapshot.time)
    gold_df = pd.DataFrame([stats.model_dump()])
    gold_path = _partition_path("gold", snapshot.time)
    storage.write_parquet(gold_path, gold_df)
    logger.info("Gold written: %s", gold_path)

    return stats

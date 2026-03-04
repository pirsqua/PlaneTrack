"""Unit tests for pipeline transformations (no network/ADLS required)."""

from datetime import UTC, datetime

import pytest

from app.models.bronze import BronzeSnapshot, StateVector
from app.models.silver import AircraftState
from app.services.pipeline import _aggregate_gold, _silver_from_bronze


def _make_state(**overrides) -> StateVector:
    defaults = dict(
        icao24="abc123",
        callsign="TEST01 ",
        origin_country="Germany",
        time_position=1700000000,
        last_contact=1700000000,
        longitude=13.4,
        latitude=52.5,
        baro_altitude=8000.0,
        on_ground=False,
        velocity=250.0,
        true_track=90.0,
        vertical_rate=0.0,
        sensors=None,
        geo_altitude=8100.0,
        squawk="1234",
        spi=False,
        position_source=0,
    )
    return StateVector(**{**defaults, **overrides})


class TestSilverTransform:
    def test_basic_conversion(self):
        sv = _make_state()
        state = AircraftState.from_bronze(sv)
        assert state is not None
        assert state.icao24 == "abc123"
        assert state.callsign == "TEST01"  # stripped
        assert isinstance(state.time_position, datetime)
        assert state.on_ground is False

    def test_missing_icao24_returns_none(self):
        sv = _make_state(icao24=None)
        assert AircraftState.from_bronze(sv) is None

    def test_empty_callsign_becomes_none(self):
        sv = _make_state(callsign="   ")
        state = AircraftState.from_bronze(sv)
        assert state is not None
        assert state.callsign is None

    def test_on_ground_defaults_false_when_none(self):
        sv = _make_state(on_ground=None)
        state = AircraftState.from_bronze(sv)
        assert state is not None
        assert state.on_ground is False

    def test_ingested_at_is_recent(self):
        sv = _make_state()
        state = AircraftState.from_bronze(sv)
        assert state is not None
        assert (datetime.now(UTC) - state.ingested_at).total_seconds() < 5


class TestSilverFromBronze:
    def test_filters_missing_icao24(self):
        snapshot = BronzeSnapshot(
            time=1700000000,
            states=[_make_state(), _make_state(icao24=None)],
        )
        result = _silver_from_bronze(snapshot)
        assert len(result) == 1

    def test_empty_snapshot(self):
        snapshot = BronzeSnapshot(time=1700000000, states=[])
        assert _silver_from_bronze(snapshot) == []


class TestStateVectorFromList:
    def test_from_list_parses_all_fields(self):
        row = [
            "abc123", "TEST01", "Germany",
            1700000000, 1700000000,
            13.4, 52.5, 8000.0, False,
            250.0, 90.0, 0.0, None,
            8100.0, "1234", False, 0,
        ]
        sv = StateVector.from_list(row)
        assert sv.icao24 == "abc123"
        assert sv.origin_country == "Germany"
        assert sv.on_ground is False

    def test_from_list_without_position_source(self):
        row = ["abc123", "TEST01", "Germany", None, None, None, None, None, True, None, None, None, None, None, None, False]
        sv = StateVector.from_list(row)
        assert sv.position_source is None


class TestAggregateGold:
    def test_counts_airborne_and_ground(self):
        states = [
            AircraftState.from_bronze(_make_state(on_ground=False)),
            AircraftState.from_bronze(_make_state(icao24="def456", on_ground=True, origin_country="France")),
            AircraftState.from_bronze(_make_state(icao24="ghi789", on_ground=False, origin_country="France")),
        ]
        stats = _aggregate_gold([s for s in states if s], 1700000000)
        assert stats.total_tracked == 3
        assert stats.total_airborne == 2
        assert stats.total_on_ground == 1
        assert stats.by_country["Germany"] == 1
        assert stats.by_country["France"] == 1  # only airborne counted

    def test_empty_states(self):
        stats = _aggregate_gold([], 1700000000)
        assert stats.total_tracked == 0
        assert stats.by_country == {}

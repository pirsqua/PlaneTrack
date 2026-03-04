"""Integration tests for API routes using TestClient with mocked dependencies."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.models.gold import FlightStats
from app.models.silver import AircraftState

# Built lazily after conftest sets env vars
def _test_settings() -> Settings:
    return Settings(
        opensky_client_id="test-client",
        opensky_client_secret="test-secret",
        azure_account_name="testaccount",
        azure_account_key="dGVzdA==",
        adls_container="test",
    )

_AIRCRAFT_SAMPLE = AircraftState(
    icao24="abc123",
    callsign="TEST01",
    origin_country="Germany",
    time_position=datetime(2024, 1, 1, tzinfo=UTC),
    last_contact=datetime(2024, 1, 1, tzinfo=UTC),
    longitude=13.4,
    latitude=52.5,
    baro_altitude_m=8000.0,
    geo_altitude_m=8100.0,
    on_ground=False,
    velocity_ms=250.0,
    true_track_deg=90.0,
    vertical_rate_ms=0.0,
    squawk="1234",
    ingested_at=datetime(2024, 1, 1, tzinfo=UTC),
)

_STATS_SAMPLE = FlightStats(
    snapshot_time=datetime(2024, 1, 1, tzinfo=UTC),
    total_tracked=1,
    total_airborne=1,
    total_on_ground=0,
    by_country={"Germany": 1},
)


@pytest.fixture
def client():
    from app.config import get_settings
    settings = _test_settings()
    get_settings.cache_clear()
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    get_settings.cache_clear()


class TestHealthRoute:
    def test_health(self, client: TestClient):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestAircraftRoutes:
    def _mock_storage(self, states: list[AircraftState]):
        import pandas as pd
        mock = MagicMock()
        mock.latest_path.return_value = "silver/2024/01/01/00/1700000000.parquet"
        mock.read_parquet.return_value = pd.DataFrame([s.model_dump() for s in states])
        return mock

    def test_list_aircraft(self, client: TestClient):
        with patch("app.api.v1.routes.aircraft.ADLSClient", return_value=self._mock_storage([_AIRCRAFT_SAMPLE])):
            resp = client.get("/api/v1/aircraft/")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["icao24"] == "abc123"

    def test_get_aircraft_found(self, client: TestClient):
        with patch("app.api.v1.routes.aircraft.ADLSClient", return_value=self._mock_storage([_AIRCRAFT_SAMPLE])):
            resp = client.get("/api/v1/aircraft/abc123")
        assert resp.status_code == 200
        assert resp.json()["callsign"] == "TEST01"

    def test_get_aircraft_not_found(self, client: TestClient):
        with patch("app.api.v1.routes.aircraft.ADLSClient", return_value=self._mock_storage([_AIRCRAFT_SAMPLE])):
            resp = client.get("/api/v1/aircraft/zzz999")
        assert resp.status_code == 404

    def test_no_data_returns_503(self, client: TestClient):
        mock = MagicMock()
        mock.latest_path.return_value = None
        with patch("app.api.v1.routes.aircraft.ADLSClient", return_value=mock):
            resp = client.get("/api/v1/aircraft/")
        assert resp.status_code == 503


class TestStatsRoute:
    def test_get_stats(self, client: TestClient):
        import pandas as pd
        mock = MagicMock()
        mock.latest_path.return_value = "gold/2024/01/01/1700000000.parquet"
        mock.read_parquet.return_value = pd.DataFrame([_STATS_SAMPLE.model_dump()])
        with patch("app.api.v1.routes.stats.ADLSClient", return_value=mock):
            resp = client.get("/api/v1/stats/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_airborne"] == 1
        assert data["by_country"] == {"Germany": 1}

    def test_no_data_returns_503(self, client: TestClient):
        mock = MagicMock()
        mock.latest_path.return_value = None
        with patch("app.api.v1.routes.stats.ADLSClient", return_value=mock):
            resp = client.get("/api/v1/stats/")
        assert resp.status_code == 503


class TestPipelineRoute:
    def test_trigger_ingest(self, client: TestClient):
        with patch("app.api.v1.routes.pipeline.run_pipeline", new_callable=AsyncMock, return_value=_STATS_SAMPLE):
            resp = client.post("/api/v1/pipeline/ingest")
        assert resp.status_code == 202
        assert resp.json()["total_tracked"] == 1

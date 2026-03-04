"""Async client for the OpenSky Network REST API."""

import logging
import time

import httpx

from app.config import Settings
from app.models.bronze import BronzeSnapshot, StateVector

logger = logging.getLogger(__name__)

_STATES_ENDPOINT = "/states/all"


class OpenSkyClient:
    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.opensky_base_url.rstrip("/")
        self._token_url = settings.opensky_token_url

        self._client_id: str = settings.opensky_client_id
        self._client_secret: str = settings.opensky_client_secret

        self._token: str | None = None
        self._token_expires_at: float = 0.0

    async def _get_token(self) -> str:
        """Return a cached bearer token, refreshing if within 30 s of expiry."""
        if self._token and time.monotonic() < self._token_expires_at - 30:
            return self._token

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                self._token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
            )
            response.raise_for_status()

        data = response.json()
        self._token = data["access_token"]
        self._token_expires_at = time.monotonic() + data.get("expires_in", 3600)
        logger.debug("OpenSky token refreshed, expires in %ds", data.get("expires_in", 3600))
        return self._token

    async def fetch_states(self) -> BronzeSnapshot:
        """Fetch all current aircraft states from OpenSky."""
        token = await self._get_token()
        url = f"{self._base_url}{_STATES_ENDPOINT}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers={"Authorization": f"Bearer {token}"})
            response.raise_for_status()

        data = response.json()
        snapshot_time: int = data.get("time", 0)
        raw_states: list[list] = data.get("states") or []

        states = [StateVector.from_list(row) for row in raw_states]
        logger.info("Fetched %d states at t=%d", len(states), snapshot_time)
        return BronzeSnapshot(time=snapshot_time, states=states)

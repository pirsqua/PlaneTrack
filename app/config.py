from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # OpenSky Network
    opensky_client_id: str
    opensky_client_secret: str
    opensky_base_url: str = "https://opensky-network.org/api"
    opensky_token_url: str = "https://opensky-network.org/api/auth/realms/opensky-network/protocol/openid-connect/token"

    # Azure Data Lake Gen2
    azure_account_name: str
    azure_account_key: str
    adls_container: str = "planetracker"

    # Pipeline
    pipeline_interval_seconds: int = Field(default=60, ge=10)

    # App
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()

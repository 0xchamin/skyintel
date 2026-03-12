from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SKYINTEL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 9096

    # Database
    #db_path: Path = Path.home() / ".osai" / "osai.db"
    db_path: Path = Path.home() / ".skyintel" / "skyintel.db"


    # OpenSky Network (OAuth2)
    opensky_client_id: str | None = None
    opensky_client_secret: str | None = None

    # Poll intervals (seconds)
    flight_poll_interval: int = 30
    satellite_poll_interval: int = 3600

    # LLM (web UI chat only)
    llm_provider: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None

    # Cesium
    cesium_ion_token: str | None = None


    @property
    def opensky_configured(self) -> bool:
        return self.opensky_client_id is not None and self.opensky_client_secret is not None

    @property
    def llm_configured(self) -> bool:
        return all([self.llm_provider, self.llm_api_key, self.llm_model])


def get_settings() -> Settings:
    return Settings()

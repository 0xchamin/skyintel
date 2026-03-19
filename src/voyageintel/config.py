from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
    )

    # Server
    host: str = "0.0.0.0"
    port: int = 9097

    # Database
    #db_path: Path = Path.home() / ".osai" / "osai.db"
    db_path: Path = Path.home() / ".voyageintel" / "voyageintel.db"

    # hub
    hub_radius_nm: int = 150
    
    # Poll intervals (seconds)
    flight_poll_interval: int = 60
    satellite_poll_interval: int = 3600

    # LLM (web UI chat only)
    llm_provider: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None

    # Cesium
    cesium_ion_token: str | None = None

    # LangFuse
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"
    langfuse_otel_host: str = "https://cloud.langfuse.com"

    # Playground
    playground_enabled: bool = True

    # AIS (maritime)
    aisstream_api_key: str | None = None
    ais_batch_flush_interval: float = 1.0      # seconds between batch writes
    ais_reconnect_delay: int = 5               # initial reconnect delay (seconds)
    vessel_prune_hours: int = 6                # remove vessels with no update after this

    # Google Maps (optional — enables geocoding)
    google_maps_api_key: str | None = None



    @property
    def llm_configured(self) -> bool:
        return all([self.llm_provider, self.llm_api_key, self.llm_model])


def get_settings() -> Settings:
    return Settings()

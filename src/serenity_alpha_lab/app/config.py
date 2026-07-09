from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class AppRuntimeConfig:
    host: str = "127.0.0.1"
    port: int = 8010
    runs_path: Path = Path("output/ui/runs.json")
    dashboard_path: Path = Path("output/ui/index.html")
    require_market_data_credentials: bool = False
    market_data_env_var: str = "SERENITY_MARKET_DATA_API_KEY"
    external_integrations_enabled: bool = False
    research_only: bool = True

    @property
    def market_data_api_key(self) -> str:
        return os.getenv(self.market_data_env_var, "").strip()

    @property
    def market_data_enabled(self) -> bool:
        return bool(self.market_data_api_key)

    def validate_startup(self) -> None:
        if self.require_market_data_credentials and not self.market_data_api_key:
            raise RuntimeError(f"Missing required market-data credential: {self.market_data_env_var}")

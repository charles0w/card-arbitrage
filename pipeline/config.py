"""Settings loaded from .env via pydantic-settings."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration in one place. Loaded from .env at the project root."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # eBay Browse API
    ebay_client_id: str = ""
    ebay_client_secret: str = ""

    # PriceCharting
    pricecharting_api_key: str = ""

    # TCGPlayer
    tcgplayer_affiliate_id: str = ""
    tcgplayer_price_feed_url: str = ""

    # Pokemon TCG API
    pokemon_tcg_api_key: str = ""

    # Output
    vault_opportunities_dir: Path = Path(
        r"C:\Users\charl\Desktop\obi-secondbrain\opportunities"
    )

    # Scout config
    scout_price_min: float = 30.0
    scout_price_max: float = 200.0
    scout_min_edge_dollars: float = 5.0
    scout_min_edge_pct: float = 0.10
    scout_min_confidence: float = 0.4
    scout_ebay_category_ids: str = "2611"  # comma-separated

    # Cache root (relative to project root unless absolute)
    cache_dir: Path = Path("data/cache")

    @property
    def ebay_categories(self) -> list[str]:
        return [c.strip() for c in self.scout_ebay_category_ids.split(",") if c.strip()]


def get_settings() -> Settings:
    """Module-level cached settings."""
    return _SETTINGS


_SETTINGS = Settings()

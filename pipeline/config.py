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

    # Scout config — price band.
    # 2026-04-28 market snapshot recommends $10 floor; snapshot also notes the
    # bulk of trackable Pokemon mispricings sit in the $10–$200 band.
    scout_price_min: float = 10.0
    scout_price_max: float = 200.0

    # Edge thresholds (defaults). Per-category overrides below.
    scout_min_edge_dollars: float = 5.0
    scout_min_edge_pct: float = 0.10
    scout_min_confidence: float = 0.4

    # Per-category alpha thresholds. From the 2026-04-28 market snapshot:
    #   - Pokemon mature singles: typical eBay-vs-TCGPlayer spread is 0–8%;
    #     >12% unusual. v1 alpha threshold: 15%.
    #   - One Piece: 5–50% spreads common, but with daily price drift that
    #     erases trade unless executed quickly. v1 alpha threshold: 25%.
    scout_min_edge_pct_pokemon: float = 0.15
    scout_min_edge_pct_one_piece: float = 0.25

    # eBay categories to scan (comma-separated string).
    # 2611 = Pokémon TCG. Add more category IDs separated by commas to widen scan.
    scout_ebay_category_ids: str = "2611"

    # Cache root.
    cache_dir: Path = Path("data/cache")

    @property
    def ebay_categories(self) -> list[str]:
        return [c.strip() for c in self.scout_ebay_category_ids.split(",") if c.strip()]

    def edge_pct_threshold_for(self, category: str) -> float:
        """Per-category minimum edge_pct threshold."""
        if category == "pokemon":
            return self.scout_min_edge_pct_pokemon
        if category == "one_piece":
            return self.scout_min_edge_pct_one_piece
        return self.scout_min_edge_pct


def get_settings() -> Settings:
    return _SETTINGS


_SETTINGS = Settings()

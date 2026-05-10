"""TCGPlayer affiliate-feed reader.

Stub implementation seeded with the 2026-04-28 market snapshot. Prices are at NM
baseline; the valuation module condition-adjusts down for LP/MP/HP listings.

The TCGPlayer Pricing API is partner-only. The realistic path is the affiliate
price-export feed: a daily ~50 MB CSV/JSON dump with market price per product.
Sign up at https://partner.tcgplayer.com/.

Real implementation will:
  1. Fetch the daily feed URL from settings.tcgplayer_price_feed_url
  2. Parse into a {product_id: market_price} mapping
  3. Cache in data/cache/tcgplayer-<date>.parquet
  4. Look up by TCGPlayer product_id (or fuzzy match on name+set as a fallback)
"""

from __future__ import annotations

import logging

from pipeline.valuation import CompTCGPlayerMarket

logger = logging.getLogger(__name__)


# TCGPlayer market price (at NM) — calibrated to typical Pokemon-mature spread
# of 0–8% above PriceCharting eBay-sold avg per the 2026-04-28 market snapshot.
# For undervalued names, market price > eBay-sold avg by 10–30%, generating the
# detectable arbitrage edge.
_STUB_MARKET: dict[str, float] = {
    # --- Pokemon: Prismatic Evolutions ---
    # Below the v1 $10 minimum price floor — these will be filtered out
    # in production runs but kept here for completeness and unit tests.
    "Sylveon ex 41 Prismatic Evolutions": 4.0,
    "Umbreon ex Prismatic Evolutions": 6.5,
    "Flareon ex 14 Prismatic Evolutions": 5.0,
    # --- Pokemon: Destined Rivals (above $10 — within scout band) ---
    "Team Rocket's Houndoom Destined Rivals": 17.0,    # 31% above PC avg → flagged
    "Cynthia's Roserade Destined Rivals": 16.5,        # 38% above PC avg → flagged
    "Piplup Destined Rivals": 18.0,                    # 24% above PC avg → flagged
    # --- Mature comps (small spread; should NOT trigger as arbitrage) ---
    "Charizard 4/102 Base Set": 110.0,
    "Lugia 9/111 Neo Genesis": 62.0,
    # --- One Piece ---
    "Luffy SR OP-01": 19.5,
}


def lookup_market(card_lookup_key: str, *, use_stub: bool | None = None) -> CompTCGPlayerMarket | None:
    """Return the TCGPlayer market price (NM baseline) for a card. None if missing.

    `use_stub`:
        - True  -> stub
        - False -> real (NotImplementedError until wired)
        - None  -> auto: real if TCGPLAYER_PRICE_FEED_URL set, else stub
    """
    if use_stub is None:
        from pipeline.config import get_settings
        use_stub = not get_settings().tcgplayer_price_feed_url
    if use_stub:
        logger.info("tcgplayer.lookup_market stub: key=%r", card_lookup_key)
        price = _STUB_MARKET.get(card_lookup_key)
        if price is None:
            return None
        return CompTCGPlayerMarket(market_price=price)
    raise NotImplementedError("Real TCGPlayer feed reader not yet wired.")


def deep_link(product_id: str, affiliate_id: str) -> str:
    """Construct a TCGPlayer deep link with affiliate tracking."""
    return f"https://www.tcgplayer.com/product/{product_id}?partner={affiliate_id}"

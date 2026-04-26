"""TCGPlayer affiliate-feed reader.

The TCGPlayer Pricing API is partner-only. The realistic path is the
affiliate price-export feed: a daily ~50 MB CSV/JSON dump with market price
per product. Sign up at https://partner.tcgplayer.com/.

Stub implementation here. Real implementation will:
  1. Fetch the daily feed URL from settings.tcgplayer_price_feed_url
  2. Parse into a {product_id: market_price} mapping
  3. Cache in data/cache/tcgplayer-<date>.parquet
  4. Look up by TCGPlayer product_id (or fuzzy match on name+set as a fallback)
"""

from __future__ import annotations

import logging

from pipeline.valuation import CompTCGPlayerMarket

logger = logging.getLogger(__name__)


_STUB_MARKET: dict[str, float] = {
    "Charizard 4/102 Base Set": 110.0,
    "Lugia 9/111 Neo Genesis": 62.0,
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

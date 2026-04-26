"""PriceCharting Premium API client — sold-comp lookups.

Stub implementation. Real client docs:
  https://www.pricecharting.com/api-documentation
"""

from __future__ import annotations

import logging

from pipeline.valuation import CompPriceCharting

logger = logging.getLogger(__name__)


# Stub data: card-name -> comp. In the real client, look up by Pokemon TCG ID.
_STUB_COMPS: dict[str, CompPriceCharting] = {
    "Charizard 4/102 Base Set": CompPriceCharting(avg=105.0, n=42, recency_days=30),
    "Lugia 9/111 Neo Genesis": CompPriceCharting(avg=58.0, n=28, recency_days=21),
    "Luffy SR OP-01": CompPriceCharting(avg=18.0, n=12, recency_days=14),
}


def lookup_comp(card_lookup_key: str, *, use_stub: bool | None = None) -> CompPriceCharting | None:
    """Return the latest sold-comp for the given card key. None if no data.

    `card_lookup_key` is a normalized "name + set" string. The real client will
    take a stable card ID instead — replace once Pokemon TCG metadata client
    is wired (`pipeline/sources/pokemon_tcg.py`).

    `use_stub`:
        - True  -> stub
        - False -> real (NotImplementedError until wired)
        - None  -> auto: real if PRICECHARTING_API_KEY set, else stub
    """
    if use_stub is None:
        from pipeline.config import get_settings
        use_stub = not get_settings().pricecharting_api_key
    if use_stub:
        logger.info("pricecharting.lookup_comp stub: key=%r", card_lookup_key)
        return _STUB_COMPS.get(card_lookup_key)
    raise NotImplementedError("Real PriceCharting client not yet wired.")

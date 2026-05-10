"""PriceCharting Premium API client — sold-comp lookups.

Stub implementation seeded with the 2026-04-28 market snapshot
(see obi-secondbrain/repos/card-arbitrage/market-snapshot-2026-04-28.md).

Real client docs: https://www.pricecharting.com/api-documentation
"""

from __future__ import annotations

import logging

from pipeline.valuation import CompPriceCharting

logger = logging.getLogger(__name__)


# Seed catalog: industry-flagged undervalued Pokemon Prismatic Evolutions / Destined Rivals
# names from the 2026-04-28 market snapshot. Recency_days reflects April-2026 capture.
# Note: One Piece coverage on PriceCharting was sparse as of 2026-04-25 — those entries
# are present here as expected placeholders but should be treated as low-confidence.
_STUB_COMPS: dict[str, CompPriceCharting] = {
    # --- Pokemon: Prismatic Evolutions (PRE) ---
    "Sylveon ex 41 Prismatic Evolutions": CompPriceCharting(avg=3.0, n=18, recency_days=30),
    "Umbreon ex Prismatic Evolutions": CompPriceCharting(avg=5.0, n=24, recency_days=20),
    "Flareon ex 14 Prismatic Evolutions": CompPriceCharting(avg=4.0, n=14, recency_days=25),
    # --- Pokemon: Destined Rivals (DR) ---
    "Team Rocket's Houndoom Destined Rivals": CompPriceCharting(avg=13.0, n=22, recency_days=18),
    "Cynthia's Roserade Destined Rivals": CompPriceCharting(avg=12.0, n=20, recency_days=21),
    "Piplup Destined Rivals": CompPriceCharting(avg=14.5, n=16, recency_days=23),
    # --- Older / "mature" comps (kept from the v0 stub for backward compatibility) ---
    "Charizard 4/102 Base Set": CompPriceCharting(avg=105.0, n=42, recency_days=30),
    "Lugia 9/111 Neo Genesis": CompPriceCharting(avg=58.0, n=28, recency_days=21),
    # --- One Piece (sparse coverage; expect no-result misses on PriceCharting in v1) ---
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

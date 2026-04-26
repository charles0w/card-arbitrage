"""Main scout loop: pull listings -> identify card -> fetch comps -> score edge.

Entry point invoked by `pipeline.cli scout`.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from pipeline.config import get_settings
from pipeline.sources import ebay, pokemon_tcg, pricecharting, tcgplayer
from pipeline.valuation import (
    EdgeResult,
    Listing,
    compute_edge,
    estimate_market_value,
)

logger = logging.getLogger(__name__)


@dataclass
class Opportunity:
    """A scored opportunity ready for rendering / logging."""

    listing_id: str
    listing_url: str
    title: str
    listing_price: float
    seller_condition: str
    seller_feedback_count: int
    seller_feedback_pct: float

    card_id: str | None
    card_name: str | None
    set_name: str | None
    set_number: str | None

    estimated_market_value: float
    estimated_market_value_confidence: float
    condition_adjusted: str
    edge_dollars: float
    edge_pct: float
    risk_buffer_pct: float
    flagged_reasons: list[str]

    listing_seen_at: str  # ISO


def scout(*, limit_per_search: int = 50, use_stub_apis: bool | None = None) -> list[Opportunity]:
    """Run one scout pass. Returns opportunities sorted by edge_dollars desc.

    `use_stub_apis`:
        - True  -> force stubs (deterministic, no API calls)
        - False -> force real API calls (will fail loudly if keys missing)
        - None  -> auto-pick: real if keys are set in .env, otherwise stub
    """
    s = get_settings()
    out: list[Opportunity] = []

    for category_id in s.ebay_categories:
        listings = ebay.search_listings(
            category_id=category_id,
            price_min=s.scout_price_min,
            price_max=s.scout_price_max,
            limit=limit_per_search,
            use_stub=use_stub_apis,
        )
        logger.info("scout: %d listings in category %s", len(listings), category_id)

        for raw in listings:
            opp = _score_one(raw, use_stub_apis=use_stub_apis)
            if opp is None:
                continue
            out.append(opp)

    # Filter by gate thresholds.
    filtered = [
        o
        for o in out
        if o.edge_dollars >= s.scout_min_edge_dollars
        and o.edge_pct >= s.scout_min_edge_pct
        and o.estimated_market_value_confidence >= s.scout_min_confidence
    ]
    filtered.sort(key=lambda o: o.edge_dollars, reverse=True)
    logger.info("scout: %d total scored, %d above threshold", len(out), len(filtered))
    return filtered


def _score_one(raw: ebay.EbayListing, *, use_stub_apis: bool | None) -> Opportunity | None:
    """Identify the card and compute edge. Returns None if no comp confidence."""
    meta = pokemon_tcg.identify_from_title(raw.title)
    if meta is None:
        # Title didn't parse. In Phase 3 this routes to the LLM-assisted detector.
        return None

    pc_comp = pricecharting.lookup_comp(meta.lookup_key, use_stub=use_stub_apis)
    tcg_comp = tcgplayer.lookup_market(meta.lookup_key, use_stub=use_stub_apis)
    # eBay sold comps deferred — Marketplace Insights API is enterprise-tier.

    market_value, confidence = estimate_market_value(
        condition=raw.seller_condition,
        pc=pc_comp,
        tcg=tcg_comp,
        ebay=None,
    )

    if confidence == 0.0:
        return None

    listing = Listing(
        listing_id=raw.listing_id,
        listing_url=raw.listing_url,
        title=raw.title,
        listing_price=raw.listing_price,
        seller_condition=raw.seller_condition,
        seller_feedback_count=raw.seller_feedback_count,
        seller_feedback_pct=raw.seller_feedback_pct,
    )
    edge: EdgeResult = compute_edge(listing, market_value, confidence)

    return Opportunity(
        listing_id=raw.listing_id,
        listing_url=raw.listing_url,
        title=raw.title,
        listing_price=raw.listing_price,
        seller_condition=raw.seller_condition,
        seller_feedback_count=raw.seller_feedback_count,
        seller_feedback_pct=raw.seller_feedback_pct,
        card_id=meta.card_id,
        card_name=meta.name,
        set_name=meta.set_name,
        set_number=meta.set_number,
        estimated_market_value=round(edge.estimated_value, 2),
        estimated_market_value_confidence=round(edge.confidence, 2),
        condition_adjusted=edge.condition_adjusted,
        edge_dollars=round(edge.edge_dollars, 2),
        edge_pct=round(edge.edge_pct, 4),
        risk_buffer_pct=edge.risk_buffer_pct,
        flagged_reasons=edge.flagged_reasons,
        listing_seen_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def opportunity_to_dict(o: Opportunity) -> dict:
    """For JSON / Parquet output."""
    return asdict(o)

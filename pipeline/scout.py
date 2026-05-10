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
    default_shipping_for_price,
    estimate_market_value,
)

logger = logging.getLogger(__name__)


@dataclass
class Opportunity:
    """A scored opportunity ready for rendering / logging.

    Two spread metrics are tracked separately:
      - `gross_spread_pct`: (market_value - listing_price) / listing_price.
        This is what the 2026-04-28 market snapshot's 15%/25% thresholds
        measure. Use this for the FILTER decision.
      - `edge_pct`: net of fees + shipping + risk buffer. Use this to decide
        whether the deal is worth chasing once it's been surfaced.
    """

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
    category: str | None  # "pokemon" | "one_piece"

    estimated_market_value: float
    estimated_market_value_confidence: float
    condition_adjusted: str
    gross_spread_dollars: float
    gross_spread_pct: float
    edge_dollars: float
    edge_pct: float
    risk_buffer_pct: float
    flagged_reasons: list[str]

    listing_seen_at: str  # ISO


def scout(*, limit_per_search: int = 50, use_stub_apis: bool | None = None) -> list[Opportunity]:
    """Run one scout pass. Returns opportunities sorted by gross_spread_dollars desc.

    Filtering matches the 2026-04-28 market snapshot's recommendation:
      - gross_spread_pct must clear the per-category threshold
        (15% pokemon, 25% one_piece by default)
      - confidence must clear scout_min_confidence
      - listing_price must clear scout_price_min ($10 default per snapshot)

    edge_dollars / edge_pct are *displayed* but not used for filtering — they
    encode whether the deal is profitable for YOUR cost structure (fees,
    shipping). Most users will want to ignore deals with negative edge_pct
    even if gross_spread is high; that's a manual decision per listing.
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

    # Filter by per-category gross-spread threshold + confidence.
    filtered = []
    for o in out:
        category_pct_floor = s.edge_pct_threshold_for(o.category or "")
        if (
            o.gross_spread_pct >= category_pct_floor
            and o.estimated_market_value_confidence >= s.scout_min_confidence
        ):
            filtered.append(o)

    filtered.sort(key=lambda o: o.gross_spread_dollars, reverse=True)
    logger.info("scout: %d total scored, %d above threshold", len(out), len(filtered))
    return filtered


def _score_one(raw: ebay.EbayListing, *, use_stub_apis: bool | None) -> Opportunity | None:
    """Identify the card and compute edge. Returns None if no comp confidence."""
    meta = pokemon_tcg.identify_from_title(raw.title)
    if meta is None:
        return None

    pc_comp = pricecharting.lookup_comp(meta.lookup_key, use_stub=use_stub_apis)
    tcg_comp = tcgplayer.lookup_market(meta.lookup_key, use_stub=use_stub_apis)

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
    ship_in, ship_out = default_shipping_for_price(raw.listing_price)
    edge: EdgeResult = compute_edge(
        listing, market_value, confidence,
        shipping_in=ship_in, shipping_out=ship_out,
    )

    # Gross spread: raw market vs listing price, before fees/shipping.
    # Uses the post-haircut market value (edge.estimated_value), so a
    # low-feedback seller's market value reflects the condition haircut.
    gross_dollars = edge.estimated_value - raw.listing_price
    gross_pct = gross_dollars / raw.listing_price if raw.listing_price > 0 else 0.0

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
        category=meta.category,
        estimated_market_value=round(edge.estimated_value, 2),
        estimated_market_value_confidence=round(edge.confidence, 2),
        condition_adjusted=edge.condition_adjusted,
        gross_spread_dollars=round(gross_dollars, 2),
        gross_spread_pct=round(gross_pct, 4),
        edge_dollars=round(edge.edge_dollars, 2),
        edge_pct=round(edge.edge_pct, 4),
        risk_buffer_pct=edge.risk_buffer_pct,
        flagged_reasons=edge.flagged_reasons,
        listing_seen_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def opportunity_to_dict(o: Opportunity) -> dict:
    return asdict(o)

"""Edge math: condition adjustment, recency weighting, market value estimation.

Mirrors `obi-secondbrain/repos/card-arbitrage/valuation-model.md`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

# ---------- Condition adjustment ----------

# Multipliers vs. NM. Anything graded handled separately.
CONDITION_MULT = {
    "M": 1.05,
    "NM": 1.00,
    "LP": 0.85,
    "MP": 0.70,
    "HP": 0.50,
    "DMG": 0.30,
}

CONDITION_NORMALIZE = {
    "mint": "M",
    "near mint": "NM",
    "near-mint": "NM",
    "nm": "NM",
    "lightly played": "LP",
    "lightly-played": "LP",
    "lp": "LP",
    "moderately played": "MP",
    "mp": "MP",
    "heavily played": "HP",
    "hp": "HP",
    "damaged": "DMG",
    "dmg": "DMG",
    "poor": "DMG",
}


def normalize_condition(raw: str | None) -> str:
    """Map a seller's condition string to a normalized code. Defaults to NM."""
    if not raw:
        return "NM"
    return CONDITION_NORMALIZE.get(raw.strip().lower(), "NM")


def condition_adjust(price_at_nm: float, condition: str) -> float:
    """Adjust an NM-baseline price down to the listed condition."""
    mult = CONDITION_MULT.get(normalize_condition(condition), 1.0)
    return price_at_nm * mult


# ---------- Recency weighting ----------


@dataclass
class Sale:
    """A historical sale comp."""

    price: float
    date: datetime


def recency_weighted_avg(sales: list[Sale], halflife_days: float = 21.0) -> float:
    """Weighted average where older sales count exponentially less."""
    if not sales:
        return 0.0
    now = datetime.now(timezone.utc)
    weights = []
    for s in sales:
        age = (now - s.date).total_seconds() / 86400.0
        w = math.exp(-math.log(2) * age / halflife_days)
        weights.append(w)
    total_w = sum(weights)
    if total_w == 0:
        return 0.0
    return sum(s.price * w for s, w in zip(sales, weights)) / total_w


# ---------- Market value estimation ----------


@dataclass
class CompPriceCharting:
    avg: float
    n: int
    recency_days: int


@dataclass
class CompTCGPlayerMarket:
    market_price: float  # at NM


@dataclass
class CompEbaySold:
    avg: float
    n: int
    recency_days: int


def estimate_market_value(
    condition: str,
    pc: CompPriceCharting | None = None,
    tcg: CompTCGPlayerMarket | None = None,
    ebay: CompEbaySold | None = None,
) -> tuple[float, float]:
    """Return (estimated_value, confidence_0_to_1)."""
    contribs: list[tuple[float, float]] = []

    if pc and pc.n >= 10 and pc.recency_days <= 90 and pc.avg > 0:
        contribs.append((pc.avg, 0.4))
    if tcg and tcg.market_price > 0:
        contribs.append((condition_adjust(tcg.market_price, condition), 0.3))
    if ebay and ebay.n >= 5 and ebay.recency_days <= 30 and ebay.avg > 0:
        contribs.append((ebay.avg, 0.3))

    if not contribs:
        return 0.0, 0.0

    total_w = sum(w for _, w in contribs)
    value = sum(v * w / total_w for v, w in contribs)
    return value, total_w


# ---------- Shipping ----------


def default_shipping_for_price(listing_price: float) -> tuple[float, float]:
    """Per-tier shipping defaults for TCG singles.

    TCG sellers ship cheap cards via Plain White Envelope (PWE) — about $2 each
    way once you account for postage + sleeve + envelope. Mid-priced cards get
    a bubble mailer with tracking (~$3.50). High-value cards get secure
    shipping with insurance (~$5+).

    The compute_edge defaults (5.0 each way) are calibrated for the high-value
    tier; use this helper from the scout to pick the right tier per listing.
    """
    if listing_price < 30.0:
        return (2.0, 2.0)
    if listing_price < 100.0:
        return (3.5, 3.5)
    return (5.0, 5.0)


# ---------- Edge computation ----------


@dataclass
class Listing:
    """A live listing on a marketplace."""

    listing_id: str
    listing_url: str
    title: str
    listing_price: float
    seller_condition: str
    seller_feedback_count: int
    seller_feedback_pct: float


@dataclass
class EdgeResult:
    edge_dollars: float
    edge_pct: float
    estimated_value: float
    confidence: float
    condition_adjusted: str
    risk_buffer_pct: float
    flagged_reasons: list[str]


def compute_edge(
    listing: Listing,
    market_value: float,
    confidence: float,
    sell_fee_pct: float = 0.13,
    shipping_in: float = 5.0,
    shipping_out: float = 5.0,
) -> EdgeResult:
    """Compute the per-listing edge.

    Mirrors valuation-model.md:
        edge_$ = market_value * (1 - sell_fee_pct)
                 - listing_price - shipping_in - shipping_out - risk_buffer

    Defaults assume high-value-card shipping. The scout calls
    `default_shipping_for_price` to override these for cheap singles.
    """
    flagged: list[str] = []
    risk_buffer_pct = 0.05
    condition_adjusted = listing.seller_condition

    # Trustworthiness haircut.
    if listing.seller_feedback_count < 50:
        risk_buffer_pct = 0.20
        flagged.append("seller_low_feedback_count")
    elif listing.seller_feedback_pct < 99.0:
        risk_buffer_pct = 0.12
        flagged.append("seller_low_feedback_pct")

    if "seller_low_feedback_count" in flagged:
        condition_adjusted = _downgrade_condition(listing.seller_condition)
        flagged.append("condition_haircut_low_feedback")
        downgrade_mult = CONDITION_MULT[normalize_condition(condition_adjusted)] / max(
            CONDITION_MULT[normalize_condition(listing.seller_condition)], 1e-9
        )
        market_value = market_value * downgrade_mult

    risk_buffer = market_value * risk_buffer_pct
    expected_proceeds = market_value * (1.0 - sell_fee_pct)
    total_cost = listing.listing_price + shipping_in + shipping_out + risk_buffer
    edge_dollars = expected_proceeds - total_cost
    edge_pct = edge_dollars / listing.listing_price if listing.listing_price > 0 else 0.0

    return EdgeResult(
        edge_dollars=edge_dollars,
        edge_pct=edge_pct,
        estimated_value=market_value,
        confidence=confidence,
        condition_adjusted=condition_adjusted,
        risk_buffer_pct=risk_buffer_pct,
        flagged_reasons=flagged,
    )


def _downgrade_condition(c: str) -> str:
    """Move one tier worse: NM -> LP -> MP -> HP -> DMG (floor)."""
    chain = ["M", "NM", "LP", "MP", "HP", "DMG"]
    code = normalize_condition(c)
    try:
        idx = chain.index(code)
        return chain[min(idx + 1, len(chain) - 1)]
    except ValueError:
        return code

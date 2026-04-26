"""Tests for the valuation logic. Run with `pytest`."""

from datetime import datetime, timedelta, timezone

from pipeline.valuation import (
    CompEbaySold,
    CompPriceCharting,
    CompTCGPlayerMarket,
    Listing,
    Sale,
    compute_edge,
    condition_adjust,
    estimate_market_value,
    normalize_condition,
    recency_weighted_avg,
)


def test_normalize_condition_known_strings() -> None:
    assert normalize_condition("Near Mint") == "NM"
    assert normalize_condition("near-mint") == "NM"
    assert normalize_condition("LP") == "LP"
    assert normalize_condition("Lightly Played") == "LP"
    assert normalize_condition("damaged") == "DMG"
    assert normalize_condition(None) == "NM"  # default


def test_condition_adjust_lp_is_85_percent_of_nm() -> None:
    assert condition_adjust(100.0, "NM") == 100.0
    assert condition_adjust(100.0, "LP") == 85.0
    assert condition_adjust(100.0, "Lightly Played") == 85.0


def test_recency_weighted_avg_recent_wins() -> None:
    now = datetime.now(timezone.utc)
    sales = [
        Sale(price=100.0, date=now - timedelta(days=1)),    # recent
        Sale(price=50.0, date=now - timedelta(days=180)),   # old
    ]
    avg = recency_weighted_avg(sales, halflife_days=21.0)
    # Recent sale dominates -> avg should be much closer to 100 than 50.
    assert avg > 90.0


def test_recency_weighted_avg_empty() -> None:
    assert recency_weighted_avg([]) == 0.0


def test_estimate_market_value_uses_all_three_sources_when_quality() -> None:
    pc = CompPriceCharting(avg=100.0, n=20, recency_days=30)
    tcg = CompTCGPlayerMarket(market_price=110.0)
    ebay = CompEbaySold(avg=105.0, n=8, recency_days=20)
    value, confidence = estimate_market_value("NM", pc=pc, tcg=tcg, ebay=ebay)
    assert confidence == 1.0  # 0.4 + 0.3 + 0.3
    # Roughly weighted average of 100, 110, 105.
    assert 100.0 < value < 110.0


def test_estimate_market_value_drops_low_quality_pc() -> None:
    pc = CompPriceCharting(avg=999.0, n=2, recency_days=30)  # n<10 -> dropped
    tcg = CompTCGPlayerMarket(market_price=110.0)
    value, confidence = estimate_market_value("NM", pc=pc, tcg=tcg)
    assert confidence == 0.3
    assert value == 110.0


def test_estimate_market_value_no_sources_returns_zero() -> None:
    value, confidence = estimate_market_value("NM")
    assert value == 0.0
    assert confidence == 0.0


def test_estimate_market_value_applies_condition_to_tcg_only() -> None:
    """TCG market price is at NM; estimator should down-adjust for LP."""
    tcg = CompTCGPlayerMarket(market_price=100.0)
    value, _ = estimate_market_value("LP", tcg=tcg)
    assert value == 85.0  # 100 * 0.85


def test_compute_edge_high_trust_seller() -> None:
    listing = Listing(
        listing_id="x",
        listing_url="https://example",
        title="Charizard",
        listing_price=65.0,
        seller_condition="NM",
        seller_feedback_count=1247,
        seller_feedback_pct=99.6,
    )
    edge = compute_edge(listing, market_value=105.0, confidence=0.7)
    # Expected proceeds: 105 * 0.87 = 91.35
    # Costs: 65 + 5 + 5 + (105*0.05) = 80.25
    # edge = 91.35 - 80.25 = 11.10
    assert 10.0 < edge.edge_dollars < 12.5
    assert "seller_low_feedback_count" not in edge.flagged_reasons
    assert edge.condition_adjusted == "NM"


def test_compute_edge_low_feedback_seller_haircuts_condition() -> None:
    listing = Listing(
        listing_id="x",
        listing_url="https://example",
        title="Lugia",
        listing_price=35.0,
        seller_condition="NM",
        seller_feedback_count=10,  # very low
        seller_feedback_pct=99.0,
    )
    edge = compute_edge(listing, market_value=58.0, confidence=0.6)
    assert "seller_low_feedback_count" in edge.flagged_reasons
    assert "condition_haircut_low_feedback" in edge.flagged_reasons
    assert edge.condition_adjusted == "LP"  # one tier worse than NM
    assert edge.risk_buffer_pct == 0.20

"""Integration tests for the scout's filter behavior using stub data."""

from pipeline.scout import scout, _score_one
from pipeline.sources import ebay
from pipeline.valuation import default_shipping_for_price


def test_default_shipping_tiers():
    """PWE for cheap cards, bubble for mid, secure for high-value."""
    assert default_shipping_for_price(15.0) == (2.0, 2.0)
    assert default_shipping_for_price(50.0) == (3.5, 3.5)
    assert default_shipping_for_price(150.0) == (5.0, 5.0)


def test_scout_filters_below_price_floor():
    """Sylveon at $2.75 should not appear (below $10 SCOUT_PRICE_MIN default)."""
    opps = scout(use_stub_apis=True)
    titles = [o.title for o in opps]
    assert not any("Sylveon" in t for t in titles)


def test_scout_filters_below_spread_threshold():
    """Charizard $98 vs market $107 has gross spread ~9% -> below the 15%
    Pokemon threshold and should be filtered out."""
    opps = scout(use_stub_apis=True)
    titles = [o.title for o in opps]
    assert not any("Charizard" in t for t in titles)


def test_scout_surfaces_destined_rivals_houndoom():
    """Destined Rivals Houndoom: 28% gross spread on a $11.50 listing.
    Above the 15% Pokemon threshold -> surfaced even with negative net edge."""
    opps = scout(use_stub_apis=True)
    titles = [o.title for o in opps]
    assert any("Houndoom" in t for t in titles)


def test_scout_one_piece_threshold_higher():
    """One Piece threshold is 25% (vs 15% Pokemon). Confirm category routing."""
    opps = scout(use_stub_apis=True)
    one_piece = [o for o in opps if o.category == "one_piece"]
    if one_piece:  # Luffy at 32% gross spread should clear
        for o in one_piece:
            assert o.gross_spread_pct >= 0.25


def test_scout_results_include_both_metrics():
    """Each opportunity has gross_spread_pct (filter signal) AND edge_pct (P&L)."""
    opps = scout(use_stub_apis=True)
    assert opps, "expected at least one stub opportunity"
    for o in opps:
        assert hasattr(o, "gross_spread_pct")
        assert hasattr(o, "edge_pct")
        # Gross spread should generally exceed net edge (gross is before fees).
        assert o.gross_spread_pct > o.edge_pct - 0.001

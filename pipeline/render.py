"""Write opportunities to per-note markdown in the Obsidian vault.

Each opportunity becomes one .md file under
  <vault>/opportunities/<YYYY-MM-DD>/<id>.md

with frontmatter that drives the Bases view.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import yaml

from pipeline.scout import Opportunity

logger = logging.getLogger(__name__)


def render_opportunities(opps: list[Opportunity], dest_root: Path) -> list[Path]:
    """Write per-opportunity notes. Returns the list of file paths written."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    day_dir = dest_root / today
    day_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for o in opps:
        path = day_dir / f"{_safe_slug(o.listing_id)}.md"
        path.write_text(_render_one(o), encoding="utf-8")
        written.append(path)
        logger.info("rendered %s", path)

    # Also emit a daily summary file at the day root.
    summary = day_dir / "_summary.md"
    summary.write_text(_render_summary(opps, today), encoding="utf-8")
    written.append(summary)

    return written


def _render_one(o: Opportunity) -> str:
    fm = {
        "card_id": o.card_id,
        "card_name": o.card_name,
        "set": o.set_name,
        "set_number": o.set_number,
        "listing_id": o.listing_id,
        "listing_url": o.listing_url,
        "listing_price": o.listing_price,
        "listing_condition_seller": o.seller_condition,
        "listing_condition_adjusted": o.condition_adjusted,
        "estimated_market_value": o.estimated_market_value,
        "estimated_market_value_confidence": o.estimated_market_value_confidence,
        "edge_dollars": o.edge_dollars,
        "edge_pct": o.edge_pct,
        "risk_buffer_pct": o.risk_buffer_pct,
        "seller_feedback_count": o.seller_feedback_count,
        "seller_feedback_pct": o.seller_feedback_pct,
        "flagged_reasons": o.flagged_reasons,
        "listing_seen_at": o.listing_seen_at,
        "tags": ["opportunity", "card-arbitrage"],
    }
    body_lines = [
        f"# {o.card_name or o.title}",
        "",
        f"> [!summary] **{o.title}**",
        f"> Listed at **${o.listing_price:.2f}** ({o.seller_condition}) — "
        f"estimated value **${o.estimated_market_value:.2f}**, edge **{o.edge_pct*100:+.1f}%** (${o.edge_dollars:+.2f})",
        "",
        f"[🛒 View / Buy on eBay]({o.listing_url})",
        "",
        "## Notes",
        "",
        "(your investigation notes here)",
    ]
    return "---\n" + yaml.safe_dump(fm, sort_keys=False) + "---\n" + "\n".join(body_lines) + "\n"


def _render_summary(opps: list[Opportunity], date: str) -> str:
    fm = {
        "type": "daily-summary",
        "date": date,
        "n_opportunities": len(opps),
        "tags": ["card-arbitrage", "summary"],
    }
    rows = ["| Card | Set | Cond | List $ | Mkt $ | Edge | Conf | Buy |", "|---|---|---|---|---|---|---|---|"]
    for o in opps[:25]:  # top 25
        rows.append(
            f"| {o.card_name or '?'} | {o.set_name or '?'} | {o.condition_adjusted} | "
            f"${o.listing_price:.2f} | ${o.estimated_market_value:.2f} | "
            f"{o.edge_pct*100:+.1f}% | {o.estimated_market_value_confidence:.2f} | "
            f"[🛒]({o.listing_url}) |"
        )
    body = (
        f"# Opportunities — {date}\n\n"
        f"**{len(opps)}** opportunities above threshold today.\n\n"
        + "\n".join(rows)
        + "\n"
    )
    return "---\n" + yaml.safe_dump(fm, sort_keys=False) + "---\n" + body


def _safe_slug(s: str) -> str:
    out = []
    for ch in s:
        if ch.isalnum() or ch in "-_":
            out.append(ch)
        else:
            out.append("-")
    return "".join(out).strip("-")[:80] or "listing"

"""eBay Browse API client.

Uses the third-party `browseapi` library (https://github.com/AverHLV/browseapi).
The library is built on aiohttp internally but exposes a synchronous
`execute()` method that manages its own event loop, so we just call it directly.

`search_listings` auto-picks between the real client and a stub based on the
`use_stub` argument. When `use_stub` is None (default), it picks real if both
EBAY_CLIENT_ID and EBAY_CLIENT_SECRET are set, otherwise stub.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EbayListing:
    listing_id: str
    listing_url: str
    title: str
    listing_price: float
    seller_condition: str
    seller_feedback_count: int
    seller_feedback_pct: float
    photo_urls: list[str]
    is_auction: bool
    end_time_iso: str | None


# ---------- public entry point ----------


def search_listings(
    *,
    category_id: str,
    price_min: float,
    price_max: float,
    limit: int = 50,
    keywords: str | None = None,
    use_stub: bool | None = None,
) -> list[EbayListing]:
    """Search eBay for active listings in a category and price band.

    `use_stub`:
        - True  -> deterministic fake data (no API calls)
        - False -> hit real Browse API; raises on missing keys
        - None  -> auto: real if both EBAY_* keys set, else stub
    """
    if use_stub is None:
        use_stub = not _have_ebay_keys()

    if use_stub:
        logger.info(
            "ebay.search_listings stub: category=%s band=%s-%s limit=%s",
            category_id, price_min, price_max, limit,
        )
        return _stub_listings(price_min, price_max, limit)

    return _real_search(
        category_id=category_id,
        price_min=price_min,
        price_max=price_max,
        limit=limit,
        keywords=keywords,
    )


def _have_ebay_keys() -> bool:
    from pipeline.config import get_settings
    s = get_settings()
    return bool(s.ebay_client_id) and bool(s.ebay_client_secret)


# ---------- stub data ----------

# Stub listings calibrated to the 2026-04-28 market snapshot:
#   - Pokemon Destined Rivals "Team Rocket's Houndoom" / "Cynthia's Roserade" / "Piplup"
#     listed below TCGPlayer market by 25-35% -> should flag as opportunities
#   - Prismatic Evolutions singles below the $10 minimum price floor -> filtered out
#   - Mature comps (Charizard, Lugia) priced near market -> low/no edge
#   - Bulk listing -> won't parse, dropped early
def _stub_listings(price_min: float, price_max: float, limit: int) -> list[EbayListing]:
    raw = [
        # --- HIGH-EDGE Pokemon Destined Rivals (above $10 floor) ---
        EbayListing(
            listing_id="ebay-stub-dr-houndoom",
            listing_url="https://www.ebay.com/itm/STUB-DR-HOUNDOOM",
            title="Team Rocket's Houndoom Destined Rivals IR",
            listing_price=11.50,
            seller_condition="Near Mint",
            seller_feedback_count=2480,
            seller_feedback_pct=99.7,
            photo_urls=["https://stub.example/photos/dr-houndoom/1.jpg"],
            is_auction=False,
            end_time_iso=None,
        ),
        EbayListing(
            listing_id="ebay-stub-dr-roserade",
            listing_url="https://www.ebay.com/itm/STUB-DR-ROSERADE",
            title="Cynthia's Roserade Destined Rivals Illustration Rare",
            listing_price=10.25,
            seller_condition="NM",
            seller_feedback_count=842,
            seller_feedback_pct=99.4,
            photo_urls=["https://stub.example/photos/dr-roserade/1.jpg"],
            is_auction=False,
            end_time_iso=None,
        ),
        EbayListing(
            listing_id="ebay-stub-dr-piplup",
            listing_url="https://www.ebay.com/itm/STUB-DR-PIPLUP",
            title="Piplup Destined Rivals Illustration Rare",
            listing_price=12.80,
            seller_condition="Near Mint",
            seller_feedback_count=1247,
            seller_feedback_pct=99.6,
            photo_urls=["https://stub.example/photos/dr-piplup/1.jpg"],
            is_auction=False,
            end_time_iso=None,
        ),
        # --- BELOW $10 floor: Prismatic Evolutions Eeveelutions ---
        EbayListing(
            listing_id="ebay-stub-pre-sylveon",
            listing_url="https://www.ebay.com/itm/STUB-PRE-SYLVEON",
            title="Sylveon ex 41 Prismatic Evolutions Double Rare",
            listing_price=2.75,
            seller_condition="NM",
            seller_feedback_count=512,
            seller_feedback_pct=99.5,
            photo_urls=[],
            is_auction=False,
            end_time_iso=None,
        ),
        # --- Mature Pokemon (Charizard) — small spread, no edge ---
        EbayListing(
            listing_id="ebay-stub-charizard",
            listing_url="https://www.ebay.com/itm/STUB-CHARIZARD",
            title="Charizard 4/102 Base Set Holo Rare",
            listing_price=98.0,  # near the $107 estimated value -> no opportunity
            seller_condition="Near Mint",
            seller_feedback_count=1247,
            seller_feedback_pct=99.6,
            photo_urls=["https://stub.example/photos/charizard/1.jpg"],
            is_auction=False,
            end_time_iso=None,
        ),
        # --- Lugia (slight under-price, but small absolute edge) ---
        EbayListing(
            listing_id="ebay-stub-lugia",
            listing_url="https://www.ebay.com/itm/STUB-LUGIA",
            title="Lugia 9/111 Neo Genesis Holo",
            listing_price=35.0,
            seller_condition="Lightly Played",
            seller_feedback_count=82,
            seller_feedback_pct=99.0,
            photo_urls=["https://stub.example/photos/lugia/1.jpg"],
            is_auction=False,
            end_time_iso=None,
        ),
        # --- One Piece: Luffy SR ---
        EbayListing(
            listing_id="ebay-stub-op01-luffy",
            listing_url="https://www.ebay.com/itm/STUB-OP01-LUFFY",
            title="Luffy SR OP-01 Romance Dawn",
            listing_price=12.0,
            seller_condition="NM",
            seller_feedback_count=45,  # low feedback - triggers haircut
            seller_feedback_pct=98.4,
            photo_urls=[],
            is_auction=False,
            end_time_iso=None,
        ),
        # --- Bulk listing: won't parse, drops early ---
        EbayListing(
            listing_id="ebay-stub-bulk",
            listing_url="https://www.ebay.com/itm/STUB-BULK",
            title="Pokemon Card Lot — bulk 100 cards mixed sets",
            listing_price=22.0,
            seller_condition="LP",
            seller_feedback_count=3500,
            seller_feedback_pct=99.9,
            photo_urls=["https://stub.example/photos/bulk/1.jpg"],
            is_auction=False,
            end_time_iso=None,
        ),
    ]
    in_band = [l for l in raw if price_min <= l.listing_price <= price_max]
    return in_band[:limit]


# ---------- real client ----------


def _real_search(
    *,
    category_id: str,
    price_min: float,
    price_max: float,
    limit: int,
    keywords: str | None,
) -> list[EbayListing]:
    """Real eBay Browse API call via the `browseapi` library."""
    from browseapi import BrowseAPI

    from pipeline.config import get_settings

    s = get_settings()

    params: dict = {
        "category_ids": str(category_id),
        "filter": (
            f"price:[{price_min:.2f}..{price_max:.2f}],"
            f"priceCurrency:USD,"
            f"buyingOptions:{{FIXED_PRICE|AUCTION}}"
        ),
        "sort": "newlyListed",
        "limit": min(limit, 200),
    }
    if keywords:
        params["q"] = keywords

    api = BrowseAPI(
        s.ebay_client_id,
        s.ebay_client_secret,
        marketplace_id="EBAY_US",
    )

    try:
        responses = api.execute("search", [params])
    except Exception as e:
        logger.exception("ebay api call failed: %s", e)
        return []

    if not responses:
        logger.warning("ebay: empty response list")
        return []

    resp = responses[0]
    if hasattr(resp, "errors") and getattr(resp, "errors", None):
        for err in resp.errors:
            logger.error(
                "ebay error %s: %s",
                getattr(err, "errorId", "?"),
                getattr(err, "message", "?"),
            )
        return []

    return _map_response(resp)


def _map_response(resp) -> list[EbayListing]:
    items = getattr(resp, "itemSummaries", None) or []
    out: list[EbayListing] = []
    for it in items:
        try:
            out.append(_map_item(it))
        except Exception as e:
            logger.warning("skipping item due to mapping error: %s (item_id=%s)", e, getattr(it, "itemId", "?"))
    logger.info("ebay: mapped %d/%d listings", len(out), len(items))
    return out


def _map_item(it) -> EbayListing:
    price = getattr(it, "price", None)
    listing_price = float(getattr(price, "value", 0.0)) if price else 0.0

    seller = getattr(it, "seller", None)
    feedback_count = int(getattr(seller, "feedbackScore", 0) or 0) if seller else 0
    feedback_pct = float(getattr(seller, "feedbackPercentage", 0.0) or 0.0) if seller else 0.0

    image = getattr(it, "image", None)
    photo_urls: list[str] = []
    if image and getattr(image, "imageUrl", None):
        photo_urls.append(image.imageUrl)
    for extra in getattr(it, "additionalImages", None) or []:
        url = getattr(extra, "imageUrl", None)
        if url:
            photo_urls.append(url)

    buying_options = getattr(it, "buyingOptions", None) or []
    is_auction = "AUCTION" in buying_options

    listing_url = (
        getattr(it, "itemAffiliateWebUrl", None)
        or getattr(it, "itemWebUrl", None)
        or ""
    )

    return EbayListing(
        listing_id=getattr(it, "itemId", "") or "",
        listing_url=listing_url,
        title=getattr(it, "title", "") or "",
        listing_price=listing_price,
        seller_condition=getattr(it, "condition", "") or "",
        seller_feedback_count=feedback_count,
        seller_feedback_pct=feedback_pct,
        photo_urls=photo_urls,
        is_auction=is_auction,
        end_time_iso=None,
    )

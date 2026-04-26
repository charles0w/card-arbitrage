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
    seller_condition: str  # raw seller-stated string
    seller_feedback_count: int
    seller_feedback_pct: float
    photo_urls: list[str]
    is_auction: bool
    end_time_iso: str | None  # populated from item detail call only


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
        - True  -> return deterministic fake data (no API calls)
        - False -> hit the real Browse API; raises if keys missing
        - None  -> auto: real if both EBAY_* keys are set, else stub
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
    """True if both EBAY_CLIENT_ID and EBAY_CLIENT_SECRET are set."""
    from pipeline.config import get_settings

    s = get_settings()
    return bool(s.ebay_client_id) and bool(s.ebay_client_secret)


# ---------- stub ----------


def _stub_listings(price_min: float, price_max: float, limit: int) -> list[EbayListing]:
    """Hand-crafted stub data exercising the valuation pipeline."""
    raw = [
        EbayListing(
            listing_id="ebay-stub-001",
            listing_url="https://www.ebay.com/itm/STUB-001",
            title="Charizard 4/102 Base Set Holo Rare",
            listing_price=65.0,
            seller_condition="Near Mint",
            seller_feedback_count=1247,
            seller_feedback_pct=99.6,
            photo_urls=["https://stub.example/photos/001/1.jpg"],
            is_auction=False,
            end_time_iso=None,
        ),
        EbayListing(
            listing_id="ebay-stub-002",
            listing_url="https://www.ebay.com/itm/STUB-002",
            title="Lugia Neo Genesis 9/111 Holo",
            listing_price=35.0,
            seller_condition="Lightly Played",
            seller_feedback_count=82,
            seller_feedback_pct=99.0,
            photo_urls=["https://stub.example/photos/002/1.jpg"],
            is_auction=False,
            end_time_iso=None,
        ),
        EbayListing(
            listing_id="ebay-stub-003",
            listing_url="https://www.ebay.com/itm/STUB-003",
            title="Luffy SR OP-01 Romance Dawn",
            listing_price=12.0,
            seller_condition="NM",
            seller_feedback_count=45,  # low — should trigger haircut
            seller_feedback_pct=98.4,
            photo_urls=[],
            is_auction=False,
            end_time_iso=None,
        ),
        EbayListing(
            listing_id="ebay-stub-004",
            listing_url="https://www.ebay.com/itm/STUB-004",
            title="Pokemon Card Lot — bulk 100 cards mixed sets",
            listing_price=22.0,
            seller_condition="LP",
            seller_feedback_count=3500,
            seller_feedback_pct=99.9,
            photo_urls=["https://stub.example/photos/004/1.jpg"],
            is_auction=False,
            end_time_iso=None,
        ),
    ]
    in_band = [
        l for l in raw if price_min <= l.listing_price <= price_max  # noqa: E741
    ]
    return in_band[:limit]


# ---------- real client (browseapi) ----------


def _real_search(
    *,
    category_id: str,
    price_min: float,
    price_max: float,
    limit: int,
    keywords: str | None,
) -> list[EbayListing]:
    """Real eBay Browse API call via the `browseapi` library.

    Notes:
      - browseapi.execute() is synchronous; it manages its own event loop
        internally. Don't wrap in asyncio.run().
      - Filter syntax follows eBay's spec:
            price:[<min>..<max>],priceCurrency:USD,buyingOptions:{FIXED_PRICE|AUCTION}
      - Keywords (`q`) is optional — eBay requires *either* `q` OR `category_ids`.
        We pass both when keywords are provided.
    """
    from browseapi import BrowseAPI  # local import so import cost is paid only when needed

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
        "limit": min(limit, 200),  # eBay API cap is 200 per page
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
    except Exception as e:  # noqa: BLE001
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
    """Map a browseapi BrowseAPIResponse to our EbayListing dataclass."""
    items = getattr(resp, "itemSummaries", None) or []
    out: list[EbayListing] = []
    for it in items:
        try:
            out.append(_map_item(it))
        except Exception as e:  # noqa: BLE001
            logger.warning("skipping item due to mapping error: %s (item_id=%s)", e, getattr(it, "itemId", "?"))
    logger.info("ebay: mapped %d/%d listings", len(out), len(items))
    return out


def _map_item(it) -> EbayListing:
    """Translate one ItemSummary to EbayListing."""
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

    # Prefer affiliate URL when present (lets future affiliate tracking work).
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
        end_time_iso=None,  # only available on get_item, not in summary
    )

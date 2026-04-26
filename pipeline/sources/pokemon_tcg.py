"""Pokemon TCG API client — card metadata.

Free API at https://pokemontcg.io. Returns set, number, rarity, image URL, etc.
Stub implementation parses the listing title heuristically.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CardMeta:
    """Identified card. `lookup_key` is what we use to fetch comps."""

    card_id: str  # canonical identifier (e.g. "base1-4")
    name: str  # "Charizard"
    set_name: str  # "Base Set"
    set_number: str  # "4/102"
    lookup_key: str  # "Charizard 4/102 Base Set"


# Heuristic patterns. The real client will hit /v2/cards?q=name:"Charizard" set.id:"base1"
# and use exact-match on the inferred set/number.
_PATTERNS = [
    # "Charizard 4/102 Base Set Holo"
    re.compile(
        r"^(?P<name>[A-Z][\w'.\- ]+?)\s+(?P<num>\d+/\d+)\s+(?P<setname>[\w ]+?)(?:\s+holo|\s+rare|$)",
        re.IGNORECASE,
    ),
    # "Lugia Neo Genesis 9/111 Holo"
    re.compile(
        r"^(?P<name>[A-Z][\w'.\- ]+?)\s+(?P<setname>[\w ]+?)\s+(?P<num>\d+/\d+)",
        re.IGNORECASE,
    ),
    # "Luffy SR OP-01 Romance Dawn"  — One Piece
    re.compile(
        r"^(?P<name>[A-Z][\w'.\- ]+?)\s+(?:SR|R|UC|C|L|SEC)\s+(?P<num>OP-\d+)\s*(?P<setname>[\w ]+)?",
        re.IGNORECASE,
    ),
]


def identify_from_title(title: str) -> CardMeta | None:
    """Heuristic title -> card identity. Returns None if title doesn't parse.

    Listings that fail this parse are candidates for the LLM-assisted detector
    (Phase 3 in the roadmap) — those are where the highest-edge mistitled
    listings hide.
    """
    title = title.strip()
    for pat in _PATTERNS:
        m = pat.match(title)
        if not m:
            continue
        name = m.group("name").strip()
        num = m.group("num").strip()
        setname = (m.groupdict().get("setname") or "").strip() or "Unknown Set"
        lookup_key = f"{name} {num} {setname}"
        return CardMeta(
            card_id=_card_id_from(name, setname, num),
            name=name,
            set_name=setname,
            set_number=num,
            lookup_key=lookup_key,
        )
    logger.info("pokemon_tcg.identify_from_title: no parse for %r", title)
    return None


def _card_id_from(name: str, set_name: str, number: str) -> str:
    """Synth a stable id from name+set+number; replace with real card_id from API."""
    slug = lambda s: re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")  # noqa: E731
    return f"{slug(set_name)}-{slug(name)}-{slug(number)}"

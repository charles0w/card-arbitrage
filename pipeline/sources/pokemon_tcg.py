"""Pokemon TCG (and One Piece) card metadata identification.

Parses noisy listing titles into structured CardMeta. Free Pokemon TCG API at
https://pokemontcg.io can replace the heuristic parser when wired up.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CardMeta:
    """Identified card. `lookup_key` is what we pass to comp lookups.

    `category` is "pokemon" or "one_piece" — the scout uses this to apply
    different spread thresholds (15% pokemon, 25% one_piece) per the
    2026-04-28 market snapshot.
    """

    card_id: str
    name: str
    set_name: str
    set_number: str
    lookup_key: str
    category: str  # "pokemon" | "one_piece"


# ---------- Known Pokemon sets ----------

# Order in this list doesn't matter for matching (we use longest-first via
# regex alternation), but does affect `_canonical_pokemon_set` lookup.
POKEMON_SETS: list[str] = [
    # Modern (most-likely targets per 2026-04-28 market snapshot)
    "Prismatic Evolutions",
    "Destined Rivals",
    # Vintage / mature
    "Base Set",
    "Jungle",
    "Fossil",
    "Team Rocket",
    "Gym Heroes",
    "Gym Challenge",
    "Neo Genesis",
    "Neo Discovery",
    "Neo Revelation",
    "Neo Destiny",
    # Modern non-target sets
    "Surging Sparks",
    "Stellar Crown",
    "Twilight Masquerade",
    "Temporal Forces",
    "Paldean Fates",
    "Paradox Rift",
    "Obsidian Flames",
    "Paldea Evolved",
    "Scarlet & Violet",
    "Crown Zenith",
    "Silver Tempest",
    "Lost Origin",
]

# Match longest patterns first so "Prismatic Evolutions" wins over a
# hypothetical future "Evolutions". Sort by length descending.
_POKEMON_SET_RE = re.compile(
    r"\b(" + "|".join(re.escape(s) for s in sorted(POKEMON_SETS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

# One Piece set codes: OP-01, EB-02, ST-10, etc.
ONE_PIECE_CODE = re.compile(r"\b(OP|EB|ST)[\s-]?(\d{1,3})\b", re.IGNORECASE)


# ---------- Public entry point ----------


def identify_from_title(title: str) -> CardMeta | None:
    """Heuristic title -> card identity. Returns None if title doesn't parse."""
    title = title.strip()
    pkm = _try_pokemon(title)
    if pkm:
        return pkm
    op = _try_one_piece(title)
    if op:
        return op
    logger.info("pokemon_tcg.identify_from_title: no parse for %r", title)
    return None


# ---------- Pokemon parser ----------


def _try_pokemon(title: str) -> CardMeta | None:
    """Match a known Pokemon set; recover name from the prefix.

    When multiple set names appear (e.g. "Team Rocket's X Destined Rivals" —
    "Team Rocket" is a 1999 set, "Destined Rivals" is the real one for this
    listing), pick the LAST match. eBay listings conventionally end with the
    set name; an earlier match is usually part of the card name.
    """
    matches = list(_POKEMON_SET_RE.finditer(title))
    if not matches:
        return None
    m = matches[-1]

    set_name = _canonical_pokemon_set(m.group(1))
    before = title[: m.start()].strip()
    after = title[m.end():].strip()

    # Pull a card-number ("4/102", "41", "207") out of either side.
    number = ""
    num_match = re.search(r"\b(\d+/\d+|\d+)\b", before + " " + after)
    if num_match:
        number = num_match.group(1)
        before = re.sub(r"\b" + re.escape(number) + r"\b", "", before).strip()

    name = _clean_card_name(before)
    if not name:
        return None

    lookup_key = f"{name} {number} {set_name}".replace("  ", " ").strip()
    return CardMeta(
        card_id=_card_id_from(name, set_name, number),
        name=name,
        set_name=set_name,
        set_number=number,
        lookup_key=lookup_key,
        category="pokemon",
    )


# ---------- One Piece parser ----------


def _try_one_piece(title: str) -> CardMeta | None:
    """Match a One Piece set code (OP-NN, EB-NN, ST-NN)."""
    m = ONE_PIECE_CODE.search(title)
    if not m:
        return None

    prefix, num = m.group(1).upper(), m.group(2).zfill(2)
    set_code = f"{prefix}-{num}"

    before = title[: m.start()].strip()
    before = re.sub(r"\b(SR|SEC|UC|R|L|C)\b", "", before, flags=re.IGNORECASE).strip()
    name = _clean_card_name(before)
    if not name:
        return None

    after = title[m.end():].strip()
    set_name_str = " ".join(after.split()[:3]) or set_code

    lookup_key = f"{name} SR {set_code}"
    return CardMeta(
        card_id=_card_id_from(name, set_code, ""),
        name=name,
        set_name=set_name_str,
        set_number=set_code,
        lookup_key=lookup_key,
        category="one_piece",
    )


# ---------- Helpers ----------


def _canonical_pokemon_set(matched: str) -> str:
    needle = matched.lower()
    for s in POKEMON_SETS:
        if s.lower() == needle:
            return s
    return matched


def _clean_card_name(s: str) -> str:
    """Strip listing-noise (holo/rare/condition/grade) from a card name."""
    if not s:
        return ""
    NOISE = (
        r"\bholo(?:graphic)?\b",
        r"\b(?:full[\s-]?art|alt[\s-]?art)\b",
        r"\b(?:secret|hyper|special|illustration|double)\s*rare\b",
        r"\b(?:IR|SR|DR|UR|HR|SIR|SAR)\b",
        r"\b(?:NM|LP|MP|HP|DMG|near[\s-]?mint|lightly[\s-]?played|moderately[\s-]?played)\b",
        r"\b(?:1st|first)\s*edition\b",
        r"\b(?:rare|common|uncommon)\b",
        r"\b(?:psa|bgs|cgc)\s*\d+\b",
        r"#\s*\d+",
    )
    for pat in NOISE:
        s = re.sub(pat, "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip(" -—,;:")
    return s


def _card_id_from(name: str, set_name: str, number: str) -> str:
    def slug(t: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")
    return f"{slug(set_name)}-{slug(name)}-{slug(number)}".strip("-")

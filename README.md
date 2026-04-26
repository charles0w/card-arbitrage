# card-arbitrage

Find undervalued Pokemon and One Piece TCG cards on eBay and TCGPlayer. Render opportunities in an Obsidian Bases view with one-click handoffs to buy / relist.

> **Strategy + design docs live in the second brain:**
> `C:\Users\charl\Desktop\obi-secondbrain\repos\card-arbitrage\`
> Start with `scoping.md` and `roadmap.md` for the why and the sequencing.

## What it does

Daily (or on-demand) scout pulls active listings from eBay's Browse API, looks up comps from PriceCharting + TCGPlayer market price, scores edge per card, and writes the top opportunities as markdown notes the Obsidian vault can render.

## Quick start

```bash
# 1. Create the venv and install
cd C:\Users\charl\Desktop\card-arbitrage
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure
copy .env.example .env
# Edit .env to add your eBay app keys and PriceCharting API key

# 3. Run the scout end-to-end (smoke test, no API calls)
python -m pipeline.cli scout --limit 5 --dry-run --stub

# 4. Run for real (auto-picks real APIs once keys are in .env)
python -m pipeline.cli scout

# Force-flags:
#   --stub  always use deterministic fake data
#   --real  always hit real APIs (errors if keys missing)
# Default: auto — real if EBAY_CLIENT_ID is set, else stub.
```

## Repo layout

```
card-arbitrage/
├── pipeline/
│   ├── __init__.py
│   ├── cli.py              # `python -m pipeline.cli ...`
│   ├── config.py           # loads .env, exposes settings
│   ├── valuation.py        # edge formula, condition adjust, recency weight
│   ├── scout.py            # main loop: fetch → comp → score → render
│   ├── render.py           # writes per-opportunity markdown to vault
│   └── sources/
│       ├── __init__.py
│       ├── ebay.py         # eBay Browse API client (active listings)
│       ├── pricecharting.py# PriceCharting Premium API (sold comps)
│       ├── tcgplayer.py    # TCGPlayer affiliate feed (market price)
│       └── pokemon_tcg.py  # Pokemon TCG API (card metadata)
├── opportunities/          # generated each scout run (gitignored)
├── inventory/              # cards you've bought + their P&L
├── data/
│   ├── cache/              # API response cache (gitignored)
│   └── catalog/            # local card metadata cache
├── tests/
│   └── test_valuation.py
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Phase 0 — what to do this weekend

Before relying on the scout, validate the loop manually. See
`obi-secondbrain/repos/card-arbitrage/roadmap.md` Phase 0:

1. Subscribe to PriceCharting Premium ($10/mo).
2. Manually scout eBay's Pokemon TCG / Singles, $30–$200 band, for 4 hours.
3. Pick the highest-conviction listing. Buy it.
4. Receive, photograph, list on TCGPlayer or eBay.
5. Track time + P&L. Decide: scale this up, or no?

The Phase 1 scout (this repo) only earns its keep if the manual loop pays back.

## Vault integration

Generated opportunities land in:

```
C:\Users\charl\Desktop\obi-secondbrain\opportunities\<YYYY-MM-DD>\<id>.md
```

The Bases view at `obi-secondbrain/opportunities/opportunities.base` renders
them as a sortable spreadsheet. Each note has a `[🛒 View on eBay]` markdown
link that opens the listing in the browser.

> **Caution about obsidian-git:** the vault auto-commits every ~2 minutes.
> Writing dozens of new notes per scout run produces commit noise. Either
> gitignore `opportunities/` in the vault, or run the scout once a day, not
> on a tight loop. See `obi-secondbrain/repos/card-arbitrage/obsidian-integration.md`.

## Status

`Phase 0` — scaffold only. Nothing makes real API calls yet — every source
client returns stubbed responses so the wiring can be tested end-to-end.
Real API integration is the first real coding task.

## License

Private. Not for redistribution.

## Bootstrapping git (one-time, when you're back at your machine)

Cowork couldn't finalize a git repo here from the sandbox — the FUSE mount
blocks deletion of the partial `.git/` folder a failed `git init` left
behind. From a real terminal on your machine:

```powershell
cd C:\Users\charl\Desktop\card-arbitrage

# 1. Delete the broken .git folder
Remove-Item -Recurse -Force .git

# 2. Initialize fresh
git init -b main
git add .
git commit -m "Initial scaffold: Python pipeline + browseapi eBay client"

# 3. Create a GitHub repo + connect
gh repo create card-arbitrage --private --source=. --remote=origin --push
# OR if you don't use gh CLI:
#   create a repo manually on github.com, then:
#   git remote add origin git@github.com:charles0w/card-arbitrage.git
#   git push -u origin main
```

"""Command-line entrypoint. `python -m pipeline.cli scout`."""

from __future__ import annotations

import json
import logging

import typer
from rich.console import Console
from rich.table import Table

from pipeline.config import get_settings
from pipeline.render import render_opportunities
from pipeline.scout import opportunity_to_dict, scout

app = typer.Typer(add_completion=False)
console = Console()


@app.command()
def scout_cmd(
    limit: int = typer.Option(50, help="Max listings per search."),
    dry_run: bool = typer.Option(False, help="Don't write to vault; print only."),
    stub: bool = typer.Option(
        False, "--stub", help="Force stub data (no API calls). Default: auto-pick based on .env keys."
    ),
    real: bool = typer.Option(
        False, "--real", help="Force real API calls (will fail if keys missing)."
    ),
    verbose: bool = typer.Option(False, "-v", help="Verbose logging."),
) -> None:
    """Run one scout pass: fetch listings -> score edge -> render opportunities."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if stub and real:
        raise typer.BadParameter("Pass at most one of --stub or --real, not both.")
    use_stub_apis: bool | None = True if stub else (False if real else None)

    s = get_settings()
    opps = scout(limit_per_search=limit, use_stub_apis=use_stub_apis)

    table = Table(title=f"Opportunities ({len(opps)})")
    for col in ("Card", "Set", "Cond", "List $", "Mkt $", "Edge $", "Edge %", "Conf"):
        table.add_column(col)
    for o in opps[:25]:
        table.add_row(
            o.card_name or "?",
            o.set_name or "?",
            o.condition_adjusted,
            f"${o.listing_price:.2f}",
            f"${o.estimated_market_value:.2f}",
            f"${o.edge_dollars:+.2f}",
            f"{o.edge_pct*100:+.1f}%",
            f"{o.estimated_market_value_confidence:.2f}",
        )
    console.print(table)

    if dry_run:
        console.print("[yellow]dry-run: not writing to vault[/yellow]")
        console.print(json.dumps([opportunity_to_dict(o) for o in opps[:3]], indent=2))
        return

    written = render_opportunities(opps, s.vault_opportunities_dir)
    console.print(f"[green]wrote {len(written)} files to {s.vault_opportunities_dir}[/green]")


# Make `python -m pipeline.cli scout` work (Typer wires `scout_cmd` as the default
# command name `scout-cmd`; rename the binding for friendlier UX).
def main() -> None:  # pragma: no cover
    app(prog_name="card-arbitrage")


# Map subcommand name without underscore.
app.command("scout")(scout_cmd)


if __name__ == "__main__":  # pragma: no cover
    main()

#!/usr/bin/env python3
"""Inspect data available in the Soft Landing backend, displayed as tables.

Usage:
    uv run python scripts/inspect_data.py                       # localhost:8000/api
    uv run python scripts/inspect_data.py --base-url https://softlanding.sussdorff.de  # production
    uv run python scripts/inspect_data.py --seed                # seed snowstorm first
    uv run python scripts/inspect_data.py --seed diversion      # seed diversion scenario
    uv run python scripts/inspect_data.py --only passengers options
"""

import argparse
import sys

import httpx
from rich.console import Console
from rich.table import Table

console = Console()

KNOWN_DISRUPTIONS = ("dis-snowstorm-001", "dis-diversion-001")


def fetch(base: str, path: str) -> list | dict:
    r = httpx.get(f"{base}{path}", timeout=10)
    r.raise_for_status()
    return r.json()


def seed_scenario(base: str, scenario: str) -> str:
    console.print(f"[yellow]Seeding scenario: {scenario}...[/yellow]")
    r = httpx.post(f"{base}/disruptions/simulate", json={"scenario": scenario}, timeout=30)
    r.raise_for_status()
    data = r.json()
    dis_id = data["id"]
    console.print(f"[green]Seeded disruption: {dis_id}[/green]")
    return dis_id


def detect_disruption(base: str) -> str | None:
    for candidate in KNOWN_DISRUPTIONS:
        try:
            r = httpx.get(f"{base}/disruptions/{candidate}", timeout=5)
            if r.status_code == 200:
                return candidate
        except httpx.RequestError:
            pass
    return None


def print_disruption(base: str, dis_id: str):
    data = fetch(base, f"/disruptions/{dis_id}")
    t = Table(title=f"Disruption: {dis_id}", show_lines=True)
    t.add_column("Field", style="bold cyan")
    t.add_column("Value")
    for key in ("id", "type", "flightNumber", "origin", "destination", "reason", "explanation", "detectedAt"):
        t.add_row(key, str(data.get(key, "")))
    pax_ids = data.get("affectedPassengerIds", [])
    t.add_row("affectedPassengers", f"{len(pax_ids)} passengers")
    console.print(t)


def print_passengers(base: str, dis_id: str) -> list:
    data = fetch(base, f"/disruptions/{dis_id}/passengers")
    t = Table(title=f"Passengers ({len(data)})", show_lines=True)
    t.add_column("ID", style="bold")
    t.add_column("Name")
    t.add_column("Booking")
    t.add_column("Status", style="bold")
    t.add_column("Priority")
    t.add_column("Denials")
    t.add_column("Itinerary")
    for p in data:
        segs = p.get("originalItinerary", [])
        itin = " → ".join(f"{s['flightNumber']} {s['origin']}-{s['destination']}" for s in segs)
        t.add_row(
            p["id"],
            p["name"],
            p["bookingRef"],
            p["status"],
            str(p.get("priority", 0)),
            str(p.get("denialCount", 0)),
            itin,
        )
    console.print(t)
    return data


def print_options(base: str, passengers: list):
    all_opts = []
    for p in passengers:
        opts = fetch(base, f"/passengers/{p['id']}/options")
        for o in opts:
            o["_passengerName"] = p["name"]
            o["_passengerId"] = p["id"]
        all_opts.extend(opts)

    t = Table(title=f"Options ({len(all_opts)})", show_lines=True)
    t.add_column("ID", style="bold")
    t.add_column("Passenger")
    t.add_column("Type", style="bold")
    t.add_column("Summary")
    t.add_column("Available")
    t.add_column("Est. Arrival")
    for o in all_opts:
        t.add_row(
            o["id"],
            f"{o['_passengerName']} ({o['_passengerId']})",
            o["type"],
            o["summary"][:60],
            "yes" if o.get("available") else "no",
            str(o.get("estimatedArrival", "")),
        )
    console.print(t)


def print_wishes(base: str, dis_id: str):
    data = fetch(base, f"/wishes?disruption_id={dis_id}")
    if not data:
        console.print("[dim]No wishes submitted yet.[/dim]")
        return
    t = Table(title=f"Wishes ({len(data)})", show_lines=True)
    t.add_column("ID", style="bold")
    t.add_column("Passenger")
    t.add_column("Selected Option")
    t.add_column("Status", style="bold")
    t.add_column("Submitted")
    t.add_column("Denial Reason")
    for w in data:
        t.add_row(
            w["id"],
            w["passengerId"],
            w["selectedOptionId"],
            w["status"],
            str(w.get("submittedAt", "")),
            w.get("denialReason") or "",
        )
    console.print(t)


def print_summary(base: str, dis_id: str, passengers: list):
    wishes = fetch(base, f"/wishes?disruption_id={dis_id}")
    statuses: dict[str, int] = {}
    for p in passengers:
        statuses[p["status"]] = statuses.get(p["status"], 0) + 1
    wish_statuses: dict[str, int] = {}
    for w in wishes:
        wish_statuses[w["status"]] = wish_statuses.get(w["status"], 0) + 1

    t = Table(title="Summary", show_lines=True)
    t.add_column("Metric", style="bold cyan")
    t.add_column("Value")
    t.add_row("Total passengers", str(len(passengers)))
    for s, c in sorted(statuses.items()):
        t.add_row(f"  └ {s}", str(c))
    t.add_row("Total wishes", str(len(wishes)))
    for s, c in sorted(wish_statuses.items()):
        t.add_row(f"  └ {s}", str(c))
    console.print(t)


def main():
    parser = argparse.ArgumentParser(description="Inspect Soft Landing backend data")
    parser.add_argument("--base-url", default="http://localhost:8000/api",
                        help="Backend base URL (default: http://localhost:8000/api)")
    parser.add_argument("--disruption-id", default=None,
                        help="Specific disruption ID (auto-detected if omitted)")
    parser.add_argument("--seed", nargs="?", const="munich_snowstorm",
                        help="Seed a scenario first: munich_snowstorm (default) or diversion")
    parser.add_argument("--only", nargs="+",
                        choices=["disruption", "passengers", "options", "wishes", "summary"],
                        help="Only show specific tables")
    parser.add_argument("--limit-options", type=int, default=20,
                        help="Max passengers to fetch options for (default: 20)")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    show_all = args.only is None
    show = set(args.only or [])

    # Check connectivity
    try:
        httpx.get(f"{base}/api/openapi.json", timeout=5)
    except httpx.RequestError:
        # Maybe the base_url already includes /api, or backend is at root
        pass

    # Seed if requested
    dis_id = args.disruption_id
    if args.seed:
        try:
            dis_id = seed_scenario(base, args.seed)
        except httpx.HTTPStatusError as e:
            console.print(f"[red]Failed to seed: {e.response.status_code} {e.response.text}[/red]")
            sys.exit(1)
        except httpx.RequestError as e:
            console.print(f"[red]Cannot reach backend at {base}: {e}[/red]")
            sys.exit(1)

    # Auto-detect disruption ID
    if not dis_id:
        console.print("[dim]Auto-detecting disruption ID...[/dim]")
        dis_id = detect_disruption(base)
        if not dis_id:
            console.print("[red]No disruption found. The database may be empty.[/red]")
            console.print("Try: [bold]uv run python scripts/inspect_data.py --seed[/bold]")
            sys.exit(1)

    console.print(f"\n[bold green]Backend:[/bold green] {base}")
    console.print(f"[bold green]Disruption:[/bold green] {dis_id}\n")

    passengers = []

    if show_all or "disruption" in show:
        print_disruption(base, dis_id)
        console.print()

    if show_all or "passengers" in show or "options" in show or "summary" in show:
        passengers = print_passengers(base, dis_id)
        console.print()

    if show_all or "options" in show:
        limited = passengers[:args.limit_options]
        if len(passengers) > args.limit_options:
            console.print(
                f"[dim](Showing options for first {args.limit_options} "
                f"of {len(passengers)} passengers, use --limit-options to change)[/dim]"
            )
        print_options(base, limited)
        console.print()

    if show_all or "wishes" in show:
        print_wishes(base, dis_id)
        console.print()

    if show_all or "summary" in show:
        print_summary(base, dis_id, passengers)
        console.print()


if __name__ == "__main__":
    main()

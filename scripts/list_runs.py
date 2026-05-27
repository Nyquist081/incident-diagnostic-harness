from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from telemetry.recorder import summarize_latest_runs  # noqa: E402


def main() -> None:
    console = Console()
    rows = summarize_latest_runs(limit=20)
    table = Table(title="Recent Incident Harness Runs")
    table.add_column("Run ID")
    table.add_column("Status")
    table.add_column("Latency ms", justify="right")
    table.add_column("Route")
    table.add_column("Query")

    for row in rows:
        table.add_row(
            row["run_id"],
            row["status"],
            str(row["total_latency_ms"] or ""),
            row["route"] or "",
            row["query"],
        )

    console.print(table)


if __name__ == "__main__":
    main()

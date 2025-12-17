from __future__ import annotations

import argparse
import os

from rich.console import Console
from rich.table import Table

from shared.brightdata import BrightDataClient
from shared.utils import load_env


console = Console()


def main() -> None:
    load_env()

    p = argparse.ArgumentParser(description="List your Bright Data dataset IDs (Scraper APIs).")
    p.add_argument("--contains", type=str, default="", help="Filter dataset name by substring (case-insensitive).")
    p.add_argument("--top", type=int, default=50, help="Max rows to show.")
    args = p.parse_args()

    api_key = os.getenv("BRIGHTDATA_API_KEY", "").strip()
    client = BrightDataClient(api_key=api_key)
    datasets = client.datasets_list()

    needle = args.contains.strip().lower()
    if needle:
        datasets = [d for d in datasets if needle in (d.get("name") or "").lower()]

    datasets = datasets[: args.top]

    t = Table(title="Bright Data datasets/list")
    t.add_column("id", style="cyan", no_wrap=True)
    t.add_column("name", style="white")
    t.add_column("size", style="magenta", justify="right")

    for d in datasets:
        t.add_row(str(d.get("id", "")), str(d.get("name", "")), str(d.get("size", "")))

    console.print(t)
    console.print("\nTip: copy a dataset id into .env as BRIGHTDATA_CHATGPT_SEARCH_DATASET_ID or custom tool config.")


if __name__ == "__main__":
    main()

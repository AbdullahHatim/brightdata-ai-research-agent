from __future__ import annotations

import argparse
import os
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from shared.brightdata import BrightDataClient
from shared.llm import LLM
from shared.utils import load_env

from basic_agent.agent import run_basic_agent


console = Console()


def main() -> None:
    load_env()

    p = argparse.ArgumentParser(description="Baseline search-only research agent (SERP).")
    p.add_argument("question", type=str, help="The research question to answer.")
    p.add_argument("--engine", type=str, default="google", choices=["google", "bing", "duckduckgo"])
    p.add_argument("--country", type=str, default=os.getenv("BRIGHTDATA_COUNTRY", "us"))
    p.add_argument("--max-results", type=int, default=10)
    p.add_argument("--out", type=str, default="outputs")
    p.add_argument("--no-llm", action="store_true", help="Skip LLM synthesis; only produce sources.json.")
    args = p.parse_args()

    api_key = os.getenv("BRIGHTDATA_API_KEY", "").strip()
    serp_zone = os.getenv("BRIGHTDATA_SERP_ZONE", "").strip()

    client = BrightDataClient(api_key=api_key)
    llm = LLM.from_env()
    if args.no_llm:
        llm = LLM(provider="none")

    run, answer_md = run_basic_agent(
        args.question,
        client=client,
        serp_zone=serp_zone,
        country=args.country,
        engine=args.engine,
        max_results=args.max_results,
        llm=llm,
        out_dir=Path(args.out),
    )

    console.print(Panel.fit(f"[bold]basic_agent finished[/bold]\nOutput: outputs/basic_agent/*", title="Done"))
    console.print(answer_md)


if __name__ == "__main__":
    main()

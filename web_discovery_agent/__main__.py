from __future__ import annotations

import argparse
import os
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from shared.brightdata import BrightDataClient
from shared.llm import LLM
from shared.utils import load_env

from web_discovery_agent.agent import run_web_discovery_agent
from web_discovery_agent.router import auto_route


console = Console()


def main() -> None:
    load_env()

    p = argparse.ArgumentParser(description="Multi-source research agent powered by Bright Data.")
    p.add_argument("question", type=str, help="The research question to answer.")
    p.add_argument("--engine", type=str, default="google", choices=["google", "bing", "duckduckgo"])
    p.add_argument("--country", type=str, default=os.getenv("BRIGHTDATA_COUNTRY", "us"))
    p.add_argument("--max-results", type=int, default=8)
    p.add_argument("--out", type=str, default="outputs")

    p.add_argument("--auto-route", action="store_true", help="Auto-enable/disable tools based on the question text.")

    p.add_argument("--no-reddit", action="store_true", help="Disable Reddit-focused SERP tool.")
    p.add_argument("--no-x", action="store_true", help="Disable X/Twitter-focused SERP tool.")
    p.add_argument("--no-answer-engine", action="store_true", help="Disable ChatGPT Search scraper tool.")
    p.add_argument("--no-archive", action="store_true", help="Disable Web Archive probe tool.")

    p.add_argument("--no-llm", action="store_true", help="Skip LLM synthesis; only produce sources.json.")
    args = p.parse_args()

    api_key = os.getenv("BRIGHTDATA_API_KEY", "").strip()
    serp_zone = os.getenv("BRIGHTDATA_SERP_ZONE", "").strip()
    client = BrightDataClient(api_key=api_key)

    llm = LLM.from_env()
    if args.no_llm:
        llm = LLM(provider="none")

    # Tool toggles
    enable_reddit = not args.no_reddit
    enable_x = not args.no_x
    enable_answer_engine = not args.no_answer_engine
    enable_archive_probe = not args.no_archive

    if args.auto_route:
        plan = auto_route(args.question)
        enable_reddit = plan.use_reddit and enable_reddit
        enable_x = plan.use_x and enable_x
        enable_answer_engine = plan.use_answer_engine and enable_answer_engine
        enable_archive_probe = plan.use_archive_probe and enable_archive_probe
        console.print(Panel.fit(plan.reason, title="Auto-route plan"))

    run, answer_md = run_web_discovery_agent(
        args.question,
        client=client,
        serp_zone=serp_zone,
        country=args.country,
        engine=args.engine,
        max_results=args.max_results,
        enable_reddit=enable_reddit,
        enable_x=enable_x,
        enable_answer_engine=enable_answer_engine,
        enable_archive_probe=enable_archive_probe,
        llm=llm,
        out_dir=Path(args.out),
    )

    console.print(Panel.fit(f"[bold]web_discovery_agent finished[/bold]\nOutput: outputs/web_discovery_agent/*", title="Done"))
    console.print(answer_md)


if __name__ == "__main__":
    main()

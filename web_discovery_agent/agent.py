from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel

from shared.brightdata import BrightDataClient
from shared.llm import LLM, LLMError
from shared.models import ResearchRun, SourceDoc
from shared.prompts import SYNTHESIS_SYSTEM, SYNTHESIS_USER
from shared.utils import ensure_dir, now_iso, stable_id

from web_discovery_agent.tools import (
    search_serp,
    search_social_reddit_serp,
    search_social_x_serp,
    run_chatgpt_search_scraper,
    parse_chatgpt_search_output,
    webarchive_probe_domain,
)

console = Console()


def build_sources_block(docs: List[SourceDoc], max_docs: int = 18) -> str:
    lines = []
    for i, d in enumerate(docs[:max_docs], start=1):
        lines.append(f"[S{i}] ({d.source_type}) {d.title}\nURL: {d.url}\nSnippet: {d.snippet}\n")
    return "\n".join(lines).strip()


def synthesize(question: str, docs: List[SourceDoc], llm: LLM) -> str:
    sources_block = build_sources_block(docs)
    messages = [
        {"role": "system", "content": SYNTHESIS_SYSTEM},
        {"role": "user", "content": SYNTHESIS_USER.format(question=question, sources_block=sources_block)},
    ]
    return llm.chat(messages)


def run_web_discovery_agent(
    question: str,
    *,
    client: BrightDataClient,
    serp_zone: str,
    country: str = "us",
    engine: str = "google",
    max_results: int = 10,
    enable_reddit: bool = True,
    enable_x: bool = True,
    enable_answer_engine: bool = True,
    enable_archive_probe: bool = True,
    llm: Optional[LLM] = None,
    out_dir: Path = Path("outputs"),
) -> Tuple[ResearchRun, str]:
    docs: List[SourceDoc] = []

    # 1) Web SERP
    docs.extend(search_serp(client, question, zone=serp_zone, country=country, engine=engine, num=max_results, source_type="serp"))

    # 2) Social SERP (Reddit + X)
    if enable_reddit:
        docs.extend(search_social_reddit_serp(client, question, zone=serp_zone, country=country, engine=engine, num=max_results))
    if enable_x:
        docs.extend(search_social_x_serp(client, question, zone=serp_zone, country=country, engine=engine, num=max_results))

    # 3) Answer engine scraper (ChatGPT Search) as a cited input
    answer_engine_meta: Dict[str, any] = {}
    if enable_answer_engine:
        dataset_id = os.getenv("BRIGHTDATA_CHATGPT_SEARCH_DATASET_ID", "").strip()
        if dataset_id:
            try:
                payload = run_chatgpt_search_scraper(
                    client,
                    prompt=question,
                    dataset_id=dataset_id,
                    country="",
                    web_search=False,
                )
                answer_engine_meta = {"chatgpt_search": {"mode": payload.get("mode"), "snapshot_id": payload.get("snapshot_id")}}
                docs.extend(parse_chatgpt_search_output(payload))
            except Exception as e:
                answer_engine_meta = {"chatgpt_search_error": str(e)}
        else:
            answer_engine_meta = {"chatgpt_search": "disabled (missing dataset_id env var)"}

    # 4) Archive probe (domain coverage)
    archive_meta: Dict[str, any] = {}
    if enable_archive_probe and docs:
        try:
            # Probe the top domain from the first SERP result (quick demo).
            top_url = docs[0].url
            domain = top_url.split("/")[2]
            probe = webarchive_probe_domain(client, domain=domain, max_age="1d")
            archive_meta = {"domain": domain, "search_id": probe["search_id"], "status": probe["status"]}
            # Add as a pseudo-source
            docs.append(
                SourceDoc(
                    source_type="archive_probe",
                    title=f"Web Archive coverage probe for {domain}",
                    url=f"https://api.brightdata.com/webarchive/search/{probe['search_id']}",
                    snippet=f"Archive search status: {probe['status']}",
                    meta={"domain": domain},
                )
            )
        except Exception as e:
            archive_meta = {"error": str(e)}

    run = ResearchRun(
        question=question,
        created_at_iso=now_iso(),
        agent_name="web_discovery_agent",
        docs=docs,
        notes={
            "engine": engine,
            "country": country,
            "serp_zone": serp_zone,
            "max_results": max_results,
            "enabled": {
                "reddit": enable_reddit,
                "x": enable_x,
                "answer_engine": enable_answer_engine,
                "archive_probe": enable_archive_probe,
            },
            "answer_engine": answer_engine_meta,
            "archive": archive_meta,
        },
    )

    if llm and llm.provider != "none":
        try:
            answer_md = synthesize(question, docs, llm)
        except LLMError as e:
            answer_md = f"# Answer\n\nLLM failed: {e}\n\n## Sources\n" + build_sources_block(docs)
    else:
        answer_md = "# Research Pack (no LLM)\n\n## Sources\n\n" + build_sources_block(docs)

    run_id = stable_id(run.created_at_iso + question)
    out_run = ensure_dir(out_dir / "web_discovery_agent" / run_id)
    (out_run / "answer.md").write_text(answer_md, encoding="utf-8")
    (out_run / "sources.json").write_text(
        __import__("json").dumps(run.to_jsonable(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return run, answer_md

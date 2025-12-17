from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel

from shared.llm import LLM, LLMError
from shared.models import ResearchRun, SourceDoc
from shared.prompts import SYNTHESIS_SYSTEM, SYNTHESIS_USER
from shared.utils import ensure_dir, now_iso, stable_id

from shared.brightdata import BrightDataClient
from basic_agent.tools import search_web_basic


console = Console()


def build_sources_block(docs: List[SourceDoc], max_docs: int = 12) -> str:
    lines = []
    for i, d in enumerate(docs[:max_docs], start=1):
        lines.append(f"[S{i}] {d.title}\nURL: {d.url}\nSnippet: {d.snippet}\n")
    return "\n".join(lines).strip()


def synthesize(question: str, docs: List[SourceDoc], llm: LLM) -> str:
    sources_block = build_sources_block(docs)
    messages = [
        {"role": "system", "content": SYNTHESIS_SYSTEM},
        {"role": "user", "content": SYNTHESIS_USER.format(question=question, sources_block=sources_block)},
    ]
    return llm.chat(messages)


def run_basic_agent(
    question: str,
    *,
    client: BrightDataClient,
    serp_zone: str,
    country: str = "us",
    engine: str = "google",
    max_results: int = 10,
    llm: Optional[LLM] = None,
    out_dir: Path = Path("outputs"),
) -> Tuple[ResearchRun, str]:
    docs = search_web_basic(client, question, zone=serp_zone, country=country, engine=engine, num=max_results)
    run = ResearchRun(
        question=question,
        created_at_iso=now_iso(),
        agent_name="basic_agent",
        docs=docs,
        notes={"engine": engine, "country": country, "serp_zone": serp_zone, "max_results": max_results},
    )

    if llm and llm.provider != "none":
        try:
            answer_md = synthesize(question, docs, llm)
        except LLMError as e:
            answer_md = f"# Answer\n\nLLM failed: {e}\n\n## Sources\n" + build_sources_block(docs)
    else:
        # No LLM: output a simple research pack
        answer_md = "# Research Pack (no LLM)\n\n## Sources\n\n" + build_sources_block(docs)

    # Write outputs
    run_id = stable_id(run.created_at_iso + question)
    out_run = ensure_dir(out_dir / "basic_agent" / run_id)
    (out_run / "answer.md").write_text(answer_md, encoding="utf-8")
    (out_run / "sources.json").write_text(
        __import__("json").dumps(run.to_jsonable(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return run, answer_md

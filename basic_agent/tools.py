from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from shared.brightdata import BrightDataClient
from shared.models import SourceDoc
from shared.utils import truncate


def build_search_url(query: str, engine: str = "google", num: int = 10, country: str = "us") -> str:
    q = quote_plus(query)
    engine = engine.lower().strip()
    if engine == "bing":
        return f"https://www.bing.com/search?q={q}&count={num}"
    if engine == "duckduckgo":
        return f"https://duckduckgo.com/?q={q}"
    # default google
    # gl=country influences country; hl=en is fine for demo
    return f"https://www.google.com/search?q={q}&num={num}&hl=en&gl={country}"


def parse_serp_results(raw: Any, source_type: str = "serp") -> List[SourceDoc]:
    """Best-effort parser for SERP JSON outputs.

    Bright Data's SERP output shape can vary depending on engine and parser settings.
    We try multiple common keys and fall back gracefully.
    """
    candidates: List[Dict[str, Any]] = []

    if isinstance(raw, list):
        candidates = [x for x in raw if isinstance(x, dict)]
    elif isinstance(raw, dict):
        for key in ["organic", "organic_results", "results", "items", "data"]:
            v = raw.get(key)
            if isinstance(v, list):
                candidates.extend([x for x in v if isinstance(x, dict)])
        # Some payloads nest results deeper
        for key in ["result", "response", "content"]:
            v = raw.get(key)
            if isinstance(v, dict):
                for k2 in ["organic", "results", "items"]:
                    vv = v.get(k2)
                    if isinstance(vv, list):
                        candidates.extend([x for x in vv if isinstance(x, dict)])

    docs: List[SourceDoc] = []
    for it in candidates:
        url = (it.get("link") or it.get("url") or it.get("href") or "").strip()
        title = (it.get("title") or it.get("name") or it.get("heading") or "").strip()
        snippet = (it.get("description") or it.get("snippet") or it.get("text") or "").strip()
        if not url:
            continue
        docs.append(
            SourceDoc(
                source_type=source_type,
                title=title or url,
                url=url,
                snippet=truncate(snippet, 280),
                published_at=it.get("date") or it.get("published") or None,
                score=float(it.get("position") or it.get("rank") or 0),
                meta={k: v for k, v in it.items() if k not in {"title", "name", "heading", "link", "url", "href", "description", "snippet", "text"}},
            )
        )

    # If parsing failed, return empty list (agent will handle)
    return docs


def search_web_basic(
    client: BrightDataClient,
    query: str,
    *,
    zone: str,
    country: str = "us",
    engine: str = "google",
    num: int = 10,
) -> List[SourceDoc]:
    target_url = build_search_url(query=query, engine=engine, num=num, country=country)
    raw = client.serp_request(zone=zone, target_url=target_url, country=country, fmt="json")
    docs = parse_serp_results(raw, source_type="serp")
    return docs

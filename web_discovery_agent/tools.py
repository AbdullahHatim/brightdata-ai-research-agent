from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

from shared.brightdata import BrightDataClient, BrightDataError
from shared.models import SourceDoc
from shared.utils import truncate

from basic_agent.tools import build_search_url, parse_serp_results


def search_serp(
    client: BrightDataClient,
    query: str,
    *,
    zone: str,
    country: str = "us",
    engine: str = "google",
    num: int = 10,
    source_type: str = "serp",
) -> List[SourceDoc]:
    target_url = build_search_url(query=query, engine=engine, num=num, country=country)
    raw = client.serp_request(zone=zone, target_url=target_url, country=country, fmt="json")
    return parse_serp_results(raw, source_type=source_type)


def search_social_reddit_serp(
    client: BrightDataClient,
    query: str,
    *,
    zone: str,
    country: str = "us",
    engine: str = "google",
    num: int = 10,
) -> List[SourceDoc]:
    # This keeps it simple + reliable: still SERP, but focused on Reddit.
    q = f"site:reddit.com {query}"
    return search_serp(client, q, zone=zone, country=country, engine=engine, num=num, source_type="reddit_serp")


def search_social_x_serp(
    client: BrightDataClient,
    query: str,
    *,
    zone: str,
    country: str = "us",
    engine: str = "google",
    num: int = 10,
) -> List[SourceDoc]:
    # X can appear as x.com or twitter.com, so we include both.
    q = f"(site:x.com OR site:twitter.com) {query}"
    return search_serp(client, q, zone=zone, country=country, engine=engine, num=num, source_type="x_serp")


def run_chatgpt_search_scraper(
    client: BrightDataClient,
    prompt: str,
    *,
    dataset_id: str,
    country: str = "",
    web_search: bool = False,
    extra_prompt: str = "",
    timeout_s: int = 180,
    poll_every_s: int = 5,
) -> Dict[str, Any]:
    """Runs Bright Data AI Answer Engine scraper (ChatGPT Search).

    We use /datasets/v3/scrape first (fast path). If it times out and returns 202,
    we poll /datasets/v3/progress/{snapshot_id} until ready, then download from
    /datasets/v3/snapshot/{snapshot_id}.
    """
    inputs = [
        {
            "url": "https://chatgpt.com/",
            "prompt": prompt,
            "country": country,
            "additional_prompt": extra_prompt,
            "web_search": bool(web_search),
        }
    ]
    status, data = client.datasets_scrape(dataset_id=dataset_id, inputs=inputs, fmt="json")
    if status == 200:
        return {"mode": "scrape", "data": data}

    # 202 path
    snapshot_id = None
    if isinstance(data, dict):
        snapshot_id = data.get("snapshot_id")
    if not snapshot_id:
        raise BrightDataError(f"Expected snapshot_id for 202 response, got: {data}")

    start = time.time()
    print(f"[Answer Engine] Status: Triggered. Waiting for snapshot... (timeout={timeout_s}s)")
    while True:
        prog = client.datasets_progress(snapshot_id)
        st = (prog.get("status") or "").lower()
        
        # UX: Simple spinner or status update
        elapsed = time.time() - start
        if elapsed % 10 < poll_every_s:  # print roughly every 10s
             print(f"[Answer Engine] Status: {st} ({int(elapsed)}s elapsed)")

        if st == "ready":
             print("[Answer Engine] Snapshot ready. Downloading...")
             break
        if st == "failed":
            raise BrightDataError(f"Snapshot failed: {prog}")
        if elapsed > timeout_s:
            raise BrightDataError(f"Timeout waiting for snapshot {snapshot_id}. Last: {prog}")
        time.sleep(poll_every_s)

    out = client.datasets_snapshot(snapshot_id, fmt="json")
    return {"mode": "async", "snapshot_id": snapshot_id, "data": out}


def parse_chatgpt_search_output(payload: Dict[str, Any]) -> List[SourceDoc]:
    """Extract citations + summary from ChatGPT Search scraper output."""
    data = payload.get("data")
    docs: List[SourceDoc] = []

    # Data might be a list of records, or a dict with records
    records: List[Dict[str, Any]] = []
    if isinstance(data, list):
        records = [r for r in data if isinstance(r, dict)]
    elif isinstance(data, dict):
        # Sometimes the API returns {status, message} or wraps records
        if "status" in data and "message" in data and not any(k in data for k in ["answer_text", "citations"]):
            return docs
        records = [data]

    for rec in records:
        answer_text = (rec.get("answer_text") or rec.get("answer_text_markdown") or "").strip()
        citations = rec.get("citations") or rec.get("sources") or []
        if isinstance(citations, list):
            for c in citations:
                if not isinstance(c, dict):
                    continue
                url = (c.get("url") or "").strip()
                title = (c.get("title") or c.get("domain") or url).strip()
                desc = (c.get("description") or "").strip()
                if not url:
                    continue
                docs.append(
                    SourceDoc(
                        source_type="answer_engine",
                        title=title,
                        url=url,
                        snippet=truncate(desc, 260),
                        meta={"engine": "chatgpt_search"},
                    )
                )
        # Include the answer itself as a pseudo-source (no URL)
        if answer_text:
            docs.append(
                SourceDoc(
                    source_type="answer_engine_answer",
                    title="ChatGPT Search (answer text)",
                    url="https://chatgpt.com/",
                    snippet=truncate(answer_text, 400),
                    meta={"engine": "chatgpt_search"},
                )
            )

    return docs


def webarchive_probe_domain(
    client: BrightDataClient,
    *,
    domain: str,
    max_age: str = "1d",
) -> Dict[str, Any]:
    """Creates a Web Archive search for a domain and returns status metadata.

    Note: Web Archive delivers full snapshots via S3/Azure/Webhook; this helper
    focuses on the *search + status* so the agent can cite 'historical coverage exists'.
    """
    search_id = client.webarchive_search(filters={"max_age": max_age, "domain_whitelist": [domain]})
    status = client.webarchive_search_status(search_id)
    return {"search_id": search_id, "status": status}

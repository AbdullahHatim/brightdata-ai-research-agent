# Architecture

## Two agents

### 1) `basic_agent/`
A **search-only** research agent.
- Gets SERP results
- Synthesizes an answer + citations from SERP sources

### 2) `web_discovery_agent/`
A **multi-source** research agent.
- Web SERP (general)
- Social SERP (targeted: Reddit + X)
- Answer engine scraper (e.g., ChatGPT Search) — treated as another cited source
- Archive (Bright Data Web Archive) — optional and usually async/offline for bigger jobs

## Design goals

- **One provider** (Bright Data) for multiple web data capabilities
- Clean, readable “YouTube demo code”
- Output a **research pack** (sources.json + answer.md)

## Files

- `shared/brightdata.py` — Bright Data API client
- `shared/llm.py` — LLM provider abstraction
- `shared/models.py` — dataclasses for sources + run outputs
- `scripts/find_datasets.py` — list dataset IDs in your account

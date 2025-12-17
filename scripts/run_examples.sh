#!/usr/bin/env bash
set -euo pipefail

cp -n .env.example .env || true

echo "1) Baseline agent"
python -m basic_agent "Should I use LangChain or LangGraph for an AI agent in 2025?" --max-results 8 --no-llm

echo ""
echo "2) Web discovery agent"
python -m web_discovery_agent "Should I use LangChain or LangGraph for an AI agent in 2025?" --max-results 6 --no-llm

echo ""
echo "Done. Check ./outputs/"

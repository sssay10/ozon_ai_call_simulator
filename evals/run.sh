#!/usr/bin/env bash
# Run all evals inside Docker — no local Python dependencies required.
#
# Usage:
#   OPENROUTER_API_KEY=sk-or-... ./run.sh
#
# With RAG (requires corp_data.xlsx ingested into ChromaDB):
#   OPENROUTER_API_KEY=sk-or-... KNOWLEDGE_RAG=1 ./run.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
    echo "ERROR: OPENROUTER_API_KEY is not set"
    exit 1
fi

echo "==> Running judge_rag eval (KNOWLEDGE_RAG=${KNOWLEDGE_RAG:-0})"
docker compose -f "$SCRIPT_DIR/docker-compose.yml" run --rm --build eval

echo ""
echo "==> Results written to evals/results/judge_rag.json"

#!/usr/bin/env bash
# Run E2E system load test: spin up the full stack, collect reports, convert to PDF.
#
# Usage:
#   ./run.sh                                        # default: 30 users, 180s
#   LOCUST_USERS=50 ./run.sh
#   LOCUST_USERS=50 LOCUST_RUN_TIME=300s LOCUST_SPAWN_RATE=5 ./run.sh
#
# LLM step:
#   Set OPENROUTER_API_KEY to include real LLM calls in the agent turn pipeline.
#   Without it, STT + TTS are still benchmarked with a fixed reply phrase.
#
# First run: downloads Silero TTS model (~100 MB) and loads T-one STT (~5 GB kenlm).
# Subsequent runs reuse the tts_model_cache Docker volume — TTS starts in ~10s.
# STT always needs ~3–4 min for kenlm.bin to load (start_period=240s).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPORTS_DIR="$SCRIPT_DIR/reports"

mkdir -p "$REPORTS_DIR"

echo "==> Starting E2E load test (users=${LOCUST_USERS:-30}, run-time=${LOCUST_RUN_TIME:-180s})"
if [[ -n "${OPENROUTER_API_KEY:-}" ]]; then
    echo "    LLM step: enabled (model=${AGENT_OPENROUTER_MODEL:-openai/gpt-4o-mini})"
else
    echo "    LLM step: disabled — STT+TTS only (set OPENROUTER_API_KEY to enable)"
fi
echo ""

COMPOSE_EXIT=0
docker compose -f "$SCRIPT_DIR/docker-compose.yml" up \
  --abort-on-container-exit \
  --exit-code-from locust \
  --build || COMPOSE_EXIT=$?

echo ""
echo "==> Converting HTML report to PDF..."
python "$SCRIPT_DIR/convert_report.py"

echo ""
echo "==> Done. Reports:"
ls -lh "$REPORTS_DIR"

exit $COMPOSE_EXIT

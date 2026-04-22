#!/usr/bin/env bash
# Run TTS load test: spin up services, collect reports, convert to PDF.
#
# Usage:
#   ./run.sh                          # default: 100 users, 120s
#   LOCUST_USERS=50 ./run.sh
#   LOCUST_USERS=100 LOCUST_RUN_TIME=180s LOCUST_SPAWN_RATE=5 ./run.sh
#
# First run downloads the Silero model (~100 MB) into a named Docker volume.
# Subsequent runs reuse the cache — startup takes ~10s instead of ~3 min.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPORTS_DIR="$SCRIPT_DIR/reports"

mkdir -p "$REPORTS_DIR"

echo "==> Starting TTS load test (users=${LOCUST_USERS:-100}, run-time=${LOCUST_RUN_TIME:-120s})"

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

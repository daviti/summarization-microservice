#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ARTIFACT_DIR="${ARTIFACT_DIR:-artifacts/run}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
HEALTH_TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-30}"

if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

rm -rf "$ARTIFACT_DIR"
mkdir -p "$ARTIFACT_DIR"

python -m uvicorn app.main:app \
  --host "$HOST" \
  --port "$PORT" \
  > "$ARTIFACT_DIR/service.log" 2>&1 &
SERVICE_PID=$!

STATUS=0

cleanup() {
  kill "$SERVICE_PID" 2>/dev/null || true
  wait "$SERVICE_PID" 2>/dev/null || true
}
trap cleanup EXIT

echo "Waiting for $BASE_URL/health ..."
waited=0
until curl -s -o /dev/null -f "$BASE_URL/health"; do
  waited=$((waited + 1))
  if [ "$waited" -ge "$HEALTH_TIMEOUT_SECONDS" ]; then
    echo "Service did not become healthy within ${HEALTH_TIMEOUT_SECONDS}s" >&2
    cat "$ARTIFACT_DIR/service.log" >&2 || true
    exit 1
  fi
  sleep 1
done
echo "Service is healthy."

echo "Running pytest..."
pytest -v > "$ARTIFACT_DIR/pytest.txt" 2>&1 || STATUS=1
tail -n 20 "$ARTIFACT_DIR/pytest.txt"

echo "Running flake8..."
flake8 app tests scripts > "$ARTIFACT_DIR/flake8.txt" 2>&1 || STATUS=1
tail -n 20 "$ARTIFACT_DIR/flake8.txt"

echo "Running pylint..."
pylint app > "$ARTIFACT_DIR/pylint.txt" 2>&1 || true
tail -n 20 "$ARTIFACT_DIR/pylint.txt"

echo "Running radon complexity analysis..."
radon cc app --show-complexity --average > "$ARTIFACT_DIR/radon.txt" 2>&1 || true
cat "$ARTIFACT_DIR/radon.txt"

tar -czf "${ARTIFACT_DIR}.tar.gz" "$ARTIFACT_DIR"
echo "Archived results to ${ARTIFACT_DIR}.tar.gz"

exit "$STATUS"

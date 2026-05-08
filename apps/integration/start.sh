#!/bin/bash
# Function: start Task 20 integration services.
# Technique used: launch Flask backend + Streamlit UI with canonical repo paths.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
UI_DIR="$REPO_ROOT/apps/streamlit"
LOG_DIR="$SCRIPT_DIR/logs"

mkdir -p "$LOG_DIR"

if ! command -v python3 &>/dev/null; then
  echo "[error] python3 not found"
  exit 1
fi

pkill -f "apps/integration/backend/api.py" 2>/dev/null || true
pkill -f "streamlit run .*apps/streamlit/main.py" 2>/dev/null || true
sleep 1

echo "[start] launching backend on :5000"
cd "$BACKEND_DIR"
PYTHONPATH="${PYTHONPATH:-}:$BACKEND_DIR:$REPO_ROOT" python3 api.py > "$LOG_DIR/backend.log" 2>&1 &
echo $! > "$LOG_DIR/backend.pid"

for i in $(seq 1 10); do
  sleep 1
  if curl -s "http://localhost:5000/api/health" >/dev/null; then
    echo "[ok] backend ready"
    break
  fi
done

echo "[start] launching streamlit UI on :8501"
cd "$UI_DIR"
PAEDIA_API_URL="http://localhost:5000" PAEDIA_USE_FIXTURES="false" streamlit run main.py \
  --server.port 8501 \
  --server.headless true \
  --server.enableCORS false \
  --browser.gatherUsageStats false > "$LOG_DIR/streamlit.log" 2>&1 &
echo $! > "$LOG_DIR/streamlit.pid"

echo "[ok] integration running"
echo "UI:      http://localhost:8501"
echo "Backend: http://localhost:5000/api/health"

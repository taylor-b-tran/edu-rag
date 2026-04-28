#!/bin/bash
# Function: stop Task 20 integration services.
# Technique used: PID-file termination with process-name fallback.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"

stop_pid_file() {
  local file="$1"
  if [ -f "$file" ]; then
    local pid
    pid="$(cat "$file")"
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      echo "[ok] stopped pid $pid"
    fi
    rm -f "$file"
  fi
}

stop_pid_file "$LOG_DIR/backend.pid"
stop_pid_file "$LOG_DIR/streamlit.pid"

pkill -f "apps/integration/backend/api.py" 2>/dev/null || true
pkill -f "streamlit run .*apps/streamlit/main.py" 2>/dev/null || true

echo "[ok] integration services stopped"

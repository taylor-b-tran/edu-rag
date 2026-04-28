#!/bin/bash
# ──────────────────────────────────────────────────────────────────
#  Paedia — Task 20 Integration Startup Script
#  CSIT321 Project 37 · Group 19
#
#  Starts:
#    1. Flask backend API  (port 5000)
#    2. Streamlit UI       (port 8501)
#
#  Usage:
#    chmod +x start.sh && ./start.sh
#
#  Environment variables:
#    PAEDIA_BACKEND_URL   — override backend URL (default: http://localhost:5000)
#    REAL_BACKEND_DIR     — path to Binh's real backend modules (optional)
# ──────────────────────────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
APP_DIR="$SCRIPT_DIR/app"
LOG_DIR="$SCRIPT_DIR/logs"

mkdir -p "$LOG_DIR"
mkdir -p "$SCRIPT_DIR/data/uploads"

# ── Colour helpers ──────────────────────────────────────────────────
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
BLUE="\033[0;34m"
NC="\033[0m"

log() { echo -e "${BLUE}[paedia]${NC} $1"; }
ok()  { echo -e "${GREEN}[ok]${NC} $1"; }
warn(){ echo -e "${YELLOW}[warn]${NC} $1"; }
err() { echo -e "${RED}[error]${NC} $1"; }

# ── Check Python ────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    err "python3 not found. Please install Python 3.10+."
    exit 1
fi

# ── Install Python deps ─────────────────────────────────────────────
log "Checking Python dependencies..."

PIP_FLAGS="--break-system-packages -q"

# Core required
python3 -c "import flask" 2>/dev/null || pip3 install flask flask-cors $PIP_FLAGS
python3 -c "import streamlit" 2>/dev/null || pip3 install streamlit $PIP_FLAGS
python3 -c "import requests" 2>/dev/null || pip3 install requests $PIP_FLAGS

# Optional real backend deps
python3 -c "import sentence_transformers" 2>/dev/null \
    && ok "sentence-transformers available (real embeddings)" \
    || warn "sentence-transformers not installed — using fixture mock (pip install sentence-transformers to enable)"

python3 -c "import chromadb" 2>/dev/null \
    && ok "chromadb available" \
    || warn "chromadb not installed — vector store unavailable in mock mode"

# ── Optionally add Binh's real backend to path ─────────────────────
if [ -n "$REAL_BACKEND_DIR" ]; then
    if [ -d "$REAL_BACKEND_DIR" ]; then
        export PYTHONPATH="$REAL_BACKEND_DIR:${PYTHONPATH:-}"
        ok "Real backend path added: $REAL_BACKEND_DIR"
    else
        warn "REAL_BACKEND_DIR='$REAL_BACKEND_DIR' does not exist — ignoring"
    fi
fi

# ── Kill any stale processes ────────────────────────────────────────
pkill -f "api.py" 2>/dev/null || true
pkill -f "streamlit run" 2>/dev/null || true
sleep 1

# ── Start Flask backend ─────────────────────────────────────────────
log "Starting Flask backend on port 5000..."
cd "$BACKEND_DIR"
PYTHONPATH="${PYTHONPATH:-}:$BACKEND_DIR" python3 api.py > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$LOG_DIR/backend.pid"

# Wait for backend to be ready
for i in $(seq 1 10); do
    sleep 1
    if curl -s http://localhost:5000/api/health &>/dev/null; then
        ok "Flask backend is up (PID $BACKEND_PID)"
        break
    fi
    if [ $i -eq 10 ]; then
        warn "Flask backend didn't respond after 10s — check logs/backend.log"
    fi
done

# ── Start Streamlit UI ──────────────────────────────────────────────
log "Starting Streamlit UI on port 8501..."
cd "$APP_DIR"
PAEDIA_BACKEND_URL="http://localhost:5000" \
PYTHONPATH="${PYTHONPATH:-}:$BACKEND_DIR" \
streamlit run main.py \
    --server.port 8501 \
    --server.headless true \
    --server.enableCORS false \
    --browser.gatherUsageStats false \
    > "$LOG_DIR/streamlit.log" 2>&1 &
STREAMLIT_PID=$!
echo $STREAMLIT_PID > "$LOG_DIR/streamlit.pid"
sleep 3

echo ""
echo -e "╔══════════════════════════════════════════════════════╗"
echo -e "║  ${GREEN}Paedia — Task 20 Integration Running${NC}               ║"
echo -e "╠══════════════════════════════════════════════════════╣"
echo -e "║  UI:      ${BLUE}http://localhost:8501${NC}                      ║"
echo -e "║  Backend: ${BLUE}http://localhost:5000/api/health${NC}            ║"
echo -e "╠══════════════════════════════════════════════════════╣"
echo -e "║  Logs:  logs/backend.log  |  logs/streamlit.log      ║"
echo -e "║  Stop:  ./stop.sh  or  Ctrl+C                        ║"
echo -e "╚══════════════════════════════════════════════════════╝"
echo ""
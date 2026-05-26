#!/usr/bin/env bash
# Auto-select the Ollama model based on detected GPU VRAM, then bring up the
# full Paedia / EduRAG Docker stack.
#
# Decision rule
#   VRAM >= VRAM_THRESHOLD_GB (default 12)  -> HIGH_VRAM_MODEL  (qwen3:14b)
#   VRAM <  VRAM_THRESHOLD_GB OR no GPU     -> LOW_VRAM_MODEL   (llama3.2)
#
# The 8-12 GB band falls into LOW_VRAM_MODEL because qwen3:14b's ~10 GB
# working set partially offloads to RAM on smaller GPUs and loses the
# speedup the model is chosen for. See docs/sprint5_implementation_summary.md
# §5 for the rationale.
#
# Overrides via env: HIGH_VRAM_MODEL, LOW_VRAM_MODEL, VRAM_THRESHOLD_GB,
# SKIP_PULL=1 (don't pull after compose up).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$REPO_ROOT/.env"
ENV_EXAMPLE="$REPO_ROOT/.env.example"

HIGH_VRAM_MODEL="${HIGH_VRAM_MODEL:-qwen3:14b}"
LOW_VRAM_MODEL="${LOW_VRAM_MODEL:-llama3.2}"
VRAM_THRESHOLD_GB="${VRAM_THRESHOLD_GB:-12}"
SKIP_PULL="${SKIP_PULL:-0}"

detect_vram_gb() {
  if ! command -v nvidia-smi >/dev/null 2>&1; then
    echo 0
    return
  fi
  local mb
  mb=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null \
       | head -n 1 \
       | tr -d '[:space:]')
  if [[ -z "$mb" || ! "$mb" =~ ^[0-9]+$ ]]; then
    echo 0
    return
  fi
  echo $(( mb / 1024 ))
}

upsert_env_var() {
  local key="$1" value="$2"
  if grep -qE "^${key}=" "$ENV_FILE"; then
    if [[ "$(uname -s)" == "Darwin" ]]; then
      sed -i '' "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
    else
      sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
    fi
  else
    printf '\n%s=%s\n' "$key" "$value" >> "$ENV_FILE"
  fi
}

vram_gb=$(detect_vram_gb)

if (( vram_gb >= VRAM_THRESHOLD_GB )); then
  chosen="$HIGH_VRAM_MODEL"
  reason="VRAM ${vram_gb} GB >= ${VRAM_THRESHOLD_GB} GB threshold"
  use_gpu_overlay=1
elif (( vram_gb > 0 )); then
  chosen="$LOW_VRAM_MODEL"
  reason="VRAM ${vram_gb} GB < ${VRAM_THRESHOLD_GB} GB threshold (partial offload would defeat speedup)"
  use_gpu_overlay=1
else
  chosen="$LOW_VRAM_MODEL"
  reason="no NVIDIA GPU detected (CPU-only path)"
  use_gpu_overlay=0
fi

echo "[start_stack] Detected GPU memory : ${vram_gb} GB"
echo "[start_stack] Selected LLM model  : ${chosen}"
echo "[start_stack] Reason              : ${reason}"

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$ENV_EXAMPLE" "$ENV_FILE"
  echo "[start_stack] Created .env from .env.example"
fi

upsert_env_var DEFAULT_OLLAMA_MODEL "$chosen"
echo "[start_stack] Wrote DEFAULT_OLLAMA_MODEL=${chosen} to .env"

compose_args=(-f "$REPO_ROOT/docker-compose.yml")
if (( use_gpu_overlay == 1 )); then
  compose_args+=(-f "$REPO_ROOT/docker-compose.gpu.yml")
  echo "[start_stack] Including docker-compose.gpu.yml overlay"
fi

cd "$REPO_ROOT"
echo "[start_stack] docker compose ${compose_args[*]} up -d --build"
docker compose "${compose_args[@]}" up -d --build

echo "[start_stack] Waiting for Ollama at http://localhost:11434/api/tags ..."
for _ in $(seq 1 30); do
  if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if [[ "$SKIP_PULL" != "1" ]]; then
  echo "[start_stack] Pulling ${chosen} into Ollama (cached if already present)..."
  docker compose "${compose_args[@]}" exec -T ollama ollama pull "$chosen"
else
  echo "[start_stack] SKIP_PULL=1 set, skipping ollama pull"
fi

echo ""
echo "[start_stack] Done."
echo "  UI       : http://localhost:8501"
echo "  API      : http://localhost:5000/api/health"
echo "  Streamlit: http://localhost:8501"
echo "  Model    : ${chosen}  (selected on ${vram_gb} GB VRAM)"

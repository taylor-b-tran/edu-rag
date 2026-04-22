# EduRAG Sprint 3 Ollama Model Selection

Date checked: 21 April 2026

## Local Hardware Summary

The hardware check was run with `scripts/check_local_hardware.ps1` and saved to `docs/hardware_check_2026-04-21.json`.

| Component | Observed value |
|---|---|
| CPU | AMD Ryzen 7 9800X3D, 8 physical cores / 16 logical processors |
| RAM | 61.56 GB |
| GPU | NVIDIA GeForce RTX 5080 |
| NVIDIA VRAM | 16,303 MiB total, 12,430 MiB free at check time |
| Driver / CUDA | NVIDIA driver 595.71, CUDA 13.2 |
| Docker | Docker 29.4.0, Docker Compose v5.1.2 |
| Disk headroom | C: drive had more than 1 TB free during selection |

## Candidate Comparison

| Candidate | Ollama size | Context | Fit assessment |
|---|---:|---:|---|
| `qwen3:8b` | 5.2 GB | 40K | Very safe and fast, but lower quality than 14B. |
| `qwen3:14b` | 9.3 GB | 40K | Best balance for the Sprint 3 test machine: higher quality than 8B while still fitting within the available 16 GB VRAM for moderate RAG context. |
| `gemma3:12b` | 8.1 GB | 128K | Good long-context alternative, but the current PoC only passes a few retrieved chunks, so the larger context window is not the main bottleneck. |
| `qwen3:30b` | 19 GB | 256K | Not recommended for the current local setup because the model size exceeds available VRAM and would likely spill to CPU/RAM. |
| `qwen3:32b` | 20 GB | 40K | Not recommended for the same reason as `qwen3:30b`. |

## Recommendation

Use `qwen3:14b` for Sprint 3 local generation.

Rationale:

- It is the strongest candidate that fits the RTX 5080 16 GB VRAM envelope with reasonable headroom for the current RAG prompt size.
- The project only sends top-K retrieved chunks to the model, so a 40K context window is enough for the current PoC.
- Larger 30B/32B candidates are likely to bottleneck by spilling beyond VRAM.
- Smaller 8B candidates are safer, but they underuse the available GPU and are less attractive for quality-focused course Q&A.

## Selected Runtime Default

```powershell
docker compose exec ollama ollama pull qwen3:14b
```

The root `.env.example`, `docker-compose.yml`, and notebook default now use:

```text
DEFAULT_OLLAMA_MODEL=qwen3:14b
```

## Validation Result

Final validation completed on 21 April 2026:

| Check | Result |
|---|---|
| `qwen3:14b` pull | Successful |
| GPU runtime | Successful when starting Ollama with the optional GPU Compose override |
| Ollama processor report | `100% GPU`, context `4096` |
| Notebook generation | Successful with `qwen3:14b` |
| Notebook fallback behaviour | Still successful for out-of-scope weather query |
| Final notebook generation mode | `qwen3:14b` |

Important implementation note:

- The first Docker run used CPU and timed out. The fix is now captured as
  `docker-compose.gpu.yml` so the base Compose stack remains CPU-safe for
  teammates. On an NVIDIA machine, start with
  `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d`.
- Qwen 3 thinking mode initially consumed the response budget. The notebook now
  sends `think: false`, `num_ctx=4096`, `num_predict=220`, and `temperature=0.2`
  for the RAG answer-generation request.

## Sources Checked

- Ollama Qwen 3 library: `https://ollama.com/library/qwen3`
- Ollama Gemma 3 library: `https://ollama.com/library/gemma3`
- Ollama Qwen 2.5 library: `https://ollama.com/library/qwen2.5`
- Ollama Llama 3.1 8B page: `https://ollama.com/library/llama3.1:8b`

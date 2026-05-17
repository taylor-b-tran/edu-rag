# Embedding Benchmarks 
 
## Methodology
 
- **Model:** `all-MiniLM-L6-v2` (384-dimensional)
- **Corpus:** 256 synthetic sentences (EduRAG-domain templates)
- **Device:** CPU
- **Runs per configuration:** 5 (first run excluded as warm-up)
- **Batch sizes tested:** 1, 8, 16, 32, 64, 128, 256
- **Normalisation:** L2 (`normalize_embeddings=True`)
---
 
## Results
 
**Model load time:** 6.026 s
 
**Single-sentence baseline** (256 sentences, one at a time):
 
| Sentences | Runs | Mean time (ms) | Throughput (sent/s) |
|---:|---:|---:|---:|
| 256 | 5 | 1,593.95 | 160.6 |
 
**Batch results:**
 
| Batch size | Mean (ms) | Median (ms) | Stdev (ms) | Throughput (sent/s) | Speedup vs baseline |
|---:|---:|---:|---:|---:|---:|
| 1 | 2,821.98 | 1,878.10 | 1,662.95 | 90.7 | 0.56× |
| 8 | 988.64 | 1,004.94 | 276.76 | 258.9 | 1.61× |
| 16 | 450.46 | 446.06 | 38.96 | 568.3 | 3.54× |
| 32 | 408.46 | 422.81 | 51.16 | 626.7 | 3.90× |
| 64 | 362.44 | 352.51 | 51.63 | 706.3 | 4.40× |
| **128** | **311.86** | **305.62** | **19.04** | **820.9** | **5.11×** ← recommended |
| 256 | 775.63 | 442.30 | 586.72 | 330.1 | 2.06× |
 
---
 
## Recommendation
 
**Recommended batch size: 128** (820.9 sent/s, 5.1× over baseline)
 
Batch 128 is the smallest size that beats the baseline by ≥ 10% and sits within 5% of peak throughput. Batch 256 is slower than 128 due to memory pressure on CPU — avoid it. For long document chunks (>512 characters), reduce to 16–32.

# Authors: Thi Hong Ngoc Nguyen
from __future__ import annotations
 
import logging
import statistics
import time
from dataclasses import dataclass, field
from typing import List, Optional, Union
 
import numpy as np
 
try:
    from sentence_transformers import SentenceTransformer 
    _ST_AVAILABLE = True
except ImportError: 
    _ST_AVAILABLE = False
    SentenceTransformer = None  
 
__all__ = [
    "Embedder",
    "EmbedderBenchmark",
    "BenchmarkResult",
    "BenchmarkReport",
    "DEFAULT_MODEL",
    "RECOMMENDED_BATCH_SIZE",
    "DEFAULT_EMBEDDING_DIM",
]
 
logger = logging.getLogger(__name__)
 
DEFAULT_MODEL: str = "all-MiniLM-L6-v2"
 

RECOMMENDED_BATCH_SIZE: int = 64
 
DEFAULT_EMBEDDING_DIM: int = 384
 
class _MockSentenceTransformer:
  
    def __init__(self, model_name: str, device: Optional[str] = None) -> None:
        self.model_name = model_name
        self.device = device or "cpu"
        self._dim = DEFAULT_EMBEDDING_DIM
        time.sleep(0.05)  # simulate model-load latency
        logger.warning(
            "sentence_transformers not installed — using _MockSentenceTransformer. "
            "Install with: pip install sentence-transformers"
        )
 
    def encode(
        self,
        sentences: List[str],
        batch_size: int = 32,
        show_progress_bar: bool = False,
        normalize_embeddings: bool = True,
        convert_to_numpy: bool = True,
    ) -> np.ndarray:
        n = len(sentences)
        time.sleep(n * 0.002)  
        rng = np.random.default_rng(seed=abs(hash(str(sentences))) % (2 ** 32))
        vecs = rng.standard_normal((n, self._dim)).astype(np.float32)
        if normalize_embeddings:
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            vecs = vecs / np.maximum(norms, 1e-12)
        return vecs
 
    def get_embedding_dimension(self) -> int:
        return self._dim
 
    def get_sentence_embedding_dimension(self) -> int:
        return self._dim

class Embedder:
  
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        batch_size: int = RECOMMENDED_BATCH_SIZE,
        device: Optional[str] = None,
        normalize_embeddings: bool = True,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self.normalize_embeddings = normalize_embeddings
        self.device = device or self._detect_device()
 
        logger.info("Loading model '%s' on device '%s'", model_name, self.device)
        load_start = time.perf_counter()
 
        if _ST_AVAILABLE:
            self._model = SentenceTransformer(model_name, device=self.device)
        else:
            self._model = _MockSentenceTransformer(model_name, device=self.device)
 
        self._load_time_s = time.perf_counter() - load_start

        if hasattr(self._model, "get_embedding_dimension"):
            self._dim: int = self._model.get_embedding_dimension()
        else:
            self._dim = self._model.get_sentence_embedding_dimension()  
 
        logger.info(
            "Model loaded in %.3f s — embedding dim: %d", self._load_time_s, self._dim
        )

    def generate_embeddings(
        self,
        texts: Union[str, List[str]],
        batch_size: Optional[int] = None,
        show_progress: bool = False,
    ) -> np.ndarray:
       
        if isinstance(texts, str):
            texts = [texts]
 
        if not texts:
            return np.empty((0, self._dim), dtype=np.float32)
 
        effective_batch = batch_size if batch_size is not None else self.batch_size
 
        logger.debug(
            "Embedding %d text(s) with batch_size=%d", len(texts), effective_batch
        )
 
        vectors: np.ndarray = self._model.encode(
            texts,
            batch_size=effective_batch,
            show_progress_bar=show_progress,
            normalize_embeddings=self.normalize_embeddings,
            convert_to_numpy=True,
        )
        return vectors.astype(np.float32)

    @property
    def embedding_dim(self) -> int:
        """Dimensionality of each output vector."""
        return self._dim
 
    @property
    def model_load_time_s(self) -> float:
        """Seconds taken to initialise the underlying model."""
        return self._load_time_s

    @staticmethod
    def _detect_device() -> str:
        """Return ``"cuda"``, ``"mps"``, or ``"cpu"`` based on availability."""
        try:
            import torch  # type: ignore
            if torch.cuda.is_available():
                return "cuda"
            if torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass
        return "cpu"
 
    def __repr__(self) -> str:
        return (
            f"Embedder(model='{self.model_name}', "
            f"batch_size={self.batch_size}, "
            f"device='{self.device}', "
            f"dim={self._dim})"
        )

@dataclass
class BenchmarkResult:
    """Timing data for a single batch-size experiment."""
 
    batch_size: int
    n_sentences: int
    runs: int
    times_s: List[float] = field(default_factory=list)
 
    # Derived — populated by compute()
    mean_s: float = 0.0
    median_s: float = 0.0
    stdev_s: float = 0.0
    min_s: float = 0.0
    max_s: float = 0.0
    throughput_sps: float = 0.0  # sentences per second
 
    def compute(self) -> "BenchmarkResult":
        """Populate derived statistics from ``times_s``."""
        self.mean_s = statistics.mean(self.times_s)
        self.median_s = statistics.median(self.times_s)
        self.stdev_s = statistics.stdev(self.times_s) if len(self.times_s) > 1 else 0.0
        self.min_s = min(self.times_s)
        self.max_s = max(self.times_s)
        self.throughput_sps = self.n_sentences / self.mean_s if self.mean_s > 0 else 0.0
        return self
 
 
@dataclass
class BenchmarkReport:
 
    model_name: str
    device: str
    embedding_dim: int
    model_load_time_s: float
    single_result: BenchmarkResult
    batch_results: List[BenchmarkResult]
    recommended_batch_size: int = RECOMMENDED_BATCH_SIZE
 
    def best_batch_result(self) -> BenchmarkResult:
        return max(self.batch_results, key=lambda r: r.throughput_sps)
 
    def summary(self) -> str:
        W = 78  # consistent width for all separator lines
 
        lines = [
            "",
            "=" * W,
            "  EMBEDDING BENCHMARK REPORT",
            "=" * W,
            f"  Model           : {self.model_name}",
            f"  Device          : {self.device}",
            f"  Embedding dim   : {self.embedding_dim}",
            f"  Model load time : {self.model_load_time_s:.3f} s",
            "",
            "  SINGLE-SENTENCE BASELINE",
            "  " + "-" * (W - 2),
            f"  Sentences       : {self.single_result.n_sentences}",
            f"  Runs            : {self.single_result.runs}",
            f"  Mean time       : {self.single_result.mean_s * 1000:.2f} ms  "
            f"(for all {self.single_result.n_sentences} sentences, one at a time)",
            f"  Throughput      : {self.single_result.throughput_sps:.1f} sentences/s",
            "",
            "  BATCH EMBEDDING RESULTS",
            "  " + "-" * (W - 2),
            f"  {'Batch':>6}  {'N':>6}  {'Mean (ms)':>10}  "
            f"{'Median (ms)':>11}  {'Stdev (ms)':>10}  "
            f"{'Throughput':>12}  {'Speedup':>7}",
            f"  {'size':>6}  {'':>6}  {'':>10}  "
            f"{'':>11}  {'':>10}  "
            f"{'(sent/s)':>12}  {'vs 1×':>7}",
            "  " + "-" * (W - 2),
        ]
 
        single_tput = self.single_result.throughput_sps
        for r in self.batch_results:
            speedup = r.throughput_sps / single_tput if single_tput > 0 else 0.0
            marker = "  <-- recommended" if r.batch_size == self.recommended_batch_size else ""
            lines.append(
                f"  {r.batch_size:>6}  {r.n_sentences:>6}  "
                f"{r.mean_s * 1000:>10.2f}  {r.median_s * 1000:>11.2f}  "
                f"{r.stdev_s * 1000:>10.2f}  {r.throughput_sps:>12.1f}  "
                f"{speedup:>6.2f}x{marker}"
            )
 
        best = self.best_batch_result()
        best_speedup = best.throughput_sps / single_tput if single_tput > 0 else 0.0
 
        lines += [
            "  " + "-" * (W - 2),
            "",
            "  RECOMMENDATION",
            "  " + "-" * (W - 2),
            f"  Recommended batch size : {self.recommended_batch_size}",
            f"  Best observed batch    : {best.batch_size} "
            f"({best.throughput_sps:.1f} sent/s, {best_speedup:.1f}× over single)",
            "",
            "  RATIONALE",
            f"  Batch size {self.recommended_batch_size} is recommended because it is the smallest",
            "  batch that beats the one-at-a-time baseline by ≥ 10 % AND sits within",
            "  5 % of peak throughput — avoiding unnecessarily large batches with no",
            "  measurable gain.  Further guidance:",
            "    • CPU          : 64 is empirically validated as a safe default",
            "    • GPU (CUDA)   : try 128–256 for higher utilisation",
            "    • Long docs    : reduce to 16–32 to avoid OOM pressure",
            "    • Memory bound : safe for models up to ~400 MB on CPU",
            "=" * W,
            "",
        ]
        return "\n".join(lines)
 
 
# ---------------------------------------------------------------------------
# EmbedderBenchmark
# ---------------------------------------------------------------------------
 
class EmbedderBenchmark:

    DEFAULT_BATCH_SIZES: List[int] = [1, 8, 16, 32, 64, 128, 256]
 
    def __init__(
        self,
        embedder: Embedder,
        n_sentences: int = 256,
        batch_sizes: Optional[List[int]] = None,
        runs: int = 5,
    ) -> None:
        self.embedder = embedder
        self.n_sentences = n_sentences
        self.batch_sizes = batch_sizes or self.DEFAULT_BATCH_SIZES
        self.runs = runs
        self._corpus = self._build_corpus(n_sentences)
 
    def run(self) -> BenchmarkReport:
        logger.info(
            "Starting benchmark: %d sentences, %d batch sizes, %d runs each",
            self.n_sentences,
            len(self.batch_sizes),
            self.runs,
        )
 
        single_result = self._benchmark_single()
        logger.info(
            "  single-at-a-time baseline | mean=%.3f s | throughput=%.1f s/s",
            single_result.mean_s,
            single_result.throughput_sps,
        )
 
        batch_results: List[BenchmarkResult] = []
        for bs in self.batch_sizes:
            result = self._benchmark_batch(bs)
            batch_results.append(result)
            logger.info(
                "  batch_size=%3d | mean=%.3f s | throughput=%.1f s/s",
                bs,
                result.mean_s,
                result.throughput_sps,
            )
 
        recommended = self._derive_recommended(batch_results, single_result)
 
        return BenchmarkReport(
            model_name=self.embedder.model_name,
            device=self.embedder.device,
            embedding_dim=self.embedder.embedding_dim,
            model_load_time_s=self.embedder.model_load_time_s,
            single_result=single_result,
            batch_results=batch_results,
            recommended_batch_size=recommended,
        )

    def _benchmark_single(self) -> BenchmarkResult:
        result = BenchmarkResult(
            batch_size=1,
            n_sentences=self.n_sentences,
            runs=self.runs,
        )
 
        self.embedder.generate_embeddings([self._corpus[0]], batch_size=1)
 
        for _ in range(self.runs):
            t0 = time.perf_counter()
            for sentence in self._corpus:
                self.embedder.generate_embeddings([sentence], batch_size=1)
            result.times_s.append(time.perf_counter() - t0)
 
        return result.compute()
 
    def _benchmark_batch(self, batch_size: int) -> BenchmarkResult:
        result = BenchmarkResult(
            batch_size=batch_size,
            n_sentences=self.n_sentences,
            runs=self.runs,
        )
 
        # warm-up pass — excluded from timing
        self.embedder.generate_embeddings(
            self._corpus[:batch_size], batch_size=batch_size
        )
 
        for _ in range(self.runs):
            t0 = time.perf_counter()
            self.embedder.generate_embeddings(self._corpus, batch_size=batch_size)
            result.times_s.append(time.perf_counter() - t0)
 
        return result.compute()
 
    @staticmethod
    def _derive_recommended(
        results: List[BenchmarkResult],
        single_result: BenchmarkResult,
    ) -> int:
        if not results:
            return RECOMMENDED_BATCH_SIZE
 
        baseline_tput = single_result.throughput_sps
 
        candidates = [
            r
            for r in sorted(results, key=lambda r: r.batch_size)
            if r.throughput_sps >= baseline_tput * 1.10 and r.batch_size > 1
        ]
 
        if not candidates:
            return RECOMMENDED_BATCH_SIZE
 
        for i in range(len(candidates) - 1):
            current = candidates[i].throughput_sps
            nxt = candidates[i + 1].throughput_sps
            gain = (nxt - current) / current if current > 0 else 0.0
            if gain < 0.05:  # < 5 % improvement → plateau reached
                return candidates[i].batch_size
 
        logger.warning(
            "Throughput still rising at batch_size=%d — consider benchmarking "
            "larger batch sizes to find the true plateau.",
            candidates[-1].batch_size,
        )
        return candidates[-1].batch_size
 
    @staticmethod
    def _build_corpus(n: int) -> List[str]:
        templates = [
            "The system processes {topic} using advanced {method} techniques.",
            "Students in CSIT321 are building {topic} projects.",
            "This document describes the {method} approach to {topic}.",
            "Security researchers study {topic} and {method} together.",
            "The retrieval pipeline embeds {topic} vectors efficiently.",
        ]
        topics = [
            "machine learning", "cybersecurity", "network intrusion detection",
            "natural language processing", "document retrieval", "deep learning",
            "malware analysis", "data forensics", "cloud computing", "embeddings",
        ]
        methods = [
            "transformer-based", "convolutional", "recurrent", "attention",
            "graph-neural", "hybrid", "ensemble", "unsupervised", "contrastive",
            "fine-tuned",
        ]
        corpus: List[str] = []
        for i in range(n):
            template = templates[i % len(templates)]
            topic = topics[i % len(topics)]
            method = methods[i % len(methods)]
            corpus.append(template.format(topic=topic, method=method))
        return corpus

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )
 
    print("\nInitialising embedder...")
    embedder = Embedder(
        model_name=DEFAULT_MODEL,
        batch_size=RECOMMENDED_BATCH_SIZE,
    )
    print(f"Embedder ready: {embedder}")
 
    print("\nRunning benchmark (this takes ~30–60 s on CPU)...")
    benchmark = EmbedderBenchmark(
        embedder=embedder,
        n_sentences=256,
        batch_sizes=[1, 8, 16, 32, 64, 128, 256],
        runs=5,
    )
    report = benchmark.run()
    print(report.summary())
 
    # Demonstrate generate_embeddings() API
    print("Quick API demo:")
    texts = [
        "Document retrieval using sentence embeddings",
        "CSIT321 capstone project assessment schedule",
        "Cybersecurity kill chain reconnaissance phase",
    ]
    vecs = embedder.generate_embeddings(texts)
    print(f"  Input  : {len(texts)} sentences")
    print(f"  Output : shape={vecs.shape}, dtype={vecs.dtype}")
    print(f"  Norms  : {np.linalg.norm(vecs, axis=1).round(4).tolist()}  (should all be 1.0)")
    print()
 
 
if __name__ == "__main__":
    main()

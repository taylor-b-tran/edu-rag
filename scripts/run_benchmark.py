import sys, os
sys.path.insert(0, os.path.abspath("."))

from src.vector_retriever.embedder import Embedder, EmbedderBenchmark

embedder = Embedder()
benchmark = EmbedderBenchmark(
    embedder=embedder,
    n_sentences=256,
    batch_sizes=[1, 8, 16, 32, 64, 128, 256],
    runs=5,
)
report = benchmark.run()
print(report.summary())
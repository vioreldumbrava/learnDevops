"""Prometheus metrics — the LLMOps signals that matter: latency, grounding, retrieval quality."""
from prometheus_client import Counter, Histogram

chat_requests = Counter(
    "dojo_ai_chat_requests_total", "Chat requests processed.", ["grounded"]
)
chat_latency = Histogram(
    "dojo_ai_chat_latency_seconds", "End-to-end chat latency in seconds."
)
retrieval_top_score = Histogram(
    "dojo_ai_retrieval_top_score",
    "Cosine score of the best retrieved chunk.",
    buckets=[0, 0.2, 0.3, 0.35, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

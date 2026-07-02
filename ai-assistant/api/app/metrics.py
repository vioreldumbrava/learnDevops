"""Prometheus metrics — the LLMOps signals that matter: latency, grounding, retrieval
quality, tokens (cost), per-stage timing, cache effectiveness, tool usage."""
from prometheus_client import Counter, Gauge, Histogram

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

# --- Lab 06: where does the time go, and what does it cost? ---
stage_latency = Histogram(
    "dojo_ai_stage_latency_seconds",
    "Latency of one pipeline stage.",
    ["stage"],  # embed | search | rerank | generate
)
time_to_first_token = Histogram(
    "dojo_ai_time_to_first_token_seconds",
    "Streaming: time from request start until the first token reaches the client.",
)
tokens_total = Counter(
    "dojo_ai_tokens_total",
    "LLM tokens consumed.",
    ["kind", "source"],  # kind: prompt|completion; source: reported|estimated
)
cache_events = Counter(
    "dojo_ai_cache_events_total", "Semantic answer-cache lookups.", ["result"]  # hit|miss
)
app_info = Gauge(
    "dojo_ai_app_info",
    "Static app info; value is always 1 (Prometheus 'info' pattern).",
    ["prompt_version", "chat_model"],
)

# --- Lab 07: agent tool usage ---
tool_calls = Counter(
    "dojo_ai_tool_calls_total", "Agent tool invocations.", ["tool", "status"]  # ok|error
)


def record_usage(usage: dict) -> None:
    """Fold one request's token usage into the counters."""
    source = "estimated" if usage.get("estimated") else "reported"
    tokens_total.labels(kind="prompt", source=source).inc(usage.get("prompt_tokens", 0))
    tokens_total.labels(kind="completion", source=source).inc(
        usage.get("completion_tokens", 0)
    )

"""Thin wrapper over the OpenAI-compatible API exposed by Ollama or LM Studio."""
from __future__ import annotations

from openai import OpenAI

from .config import cfg

# One client for both chat and embeddings. Swapping backends is just a base_url
# change (OPENAI_BASE_URL) — no code changes.
client = OpenAI(
    base_url=cfg.OPENAI_BASE_URL,
    api_key=cfg.OPENAI_API_KEY,
    timeout=cfg.REQUEST_TIMEOUT,
)


def embed(texts: list[str]) -> list[list[float]]:
    """Return an embedding vector per input string."""
    resp = client.embeddings.create(model=cfg.EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]


def _usage_dict(usage, messages: list[dict] | None, text: str) -> dict:
    """Normalize the API's usage block; estimate when the backend omits it.

    The API is the source of truth for token counts — a local tokenizer library
    (tiktoken) would be wrong for llama-family models anyway. The ~4 chars/token
    estimate is clearly labeled so dashboards can tell real from approximate.
    """
    if usage is not None:
        return {
            "prompt_tokens": usage.prompt_tokens or 0,
            "completion_tokens": usage.completion_tokens or 0,
            "estimated": False,
        }
    prompt_chars = sum(len(m.get("content") or "") for m in (messages or []))
    return {
        "prompt_tokens": max(1, prompt_chars // 4),
        "completion_tokens": max(1, len(text) // 4) if text else 0,
        "estimated": True,
    }


def chat(messages: list[dict], stream: bool = False):
    """Chat completion.

    stream=False -> {"text": str, "usage": {prompt_tokens, completion_tokens, estimated}}
    stream=True  -> generator of {"type": "token", "text": ...} events, ending
                    with one {"type": "usage", ...} event.
    """
    kwargs = {}
    if stream:
        # Ask the backend to append a final chunk carrying token usage.
        kwargs["stream_options"] = {"include_usage": True}
    resp = client.chat.completions.create(
        model=cfg.CHAT_MODEL,
        messages=messages,
        temperature=0.2,
        stream=stream,
        **kwargs,
    )
    if not stream:
        text = resp.choices[0].message.content or ""
        return {"text": text, "usage": _usage_dict(getattr(resp, "usage", None), messages, text)}

    def events():
        usage = None
        parts: list[str] = []
        for chunk in resp:
            # The include_usage final chunk has an EMPTY choices list — indexing
            # chunk.choices[0] without this guard is the classic streaming crash.
            if chunk.choices:
                delta = chunk.choices[0].delta.content
                if delta:
                    parts.append(delta)
                    yield {"type": "token", "text": delta}
            if getattr(chunk, "usage", None):
                usage = chunk.usage
        yield {"type": "usage", **_usage_dict(usage, messages, "".join(parts))}

    return events()


def chat_raw(messages: list[dict], tools: list[dict] | None = None):
    """Full completion object, optionally with tool schemas — the agent loop
    (lab 07) needs the raw message to read `tool_calls`, not just its text.
    Non-streaming by design: tool calls over streaming are unreliable on
    local OpenAI-compatible backends."""
    kwargs = {"tools": tools} if tools else {}
    return client.chat.completions.create(
        model=cfg.CHAT_MODEL,
        messages=messages,
        temperature=0.2,
        **kwargs,
    )

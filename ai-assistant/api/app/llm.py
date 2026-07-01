"""Thin wrapper over the OpenAI-compatible API exposed by Ollama or LM Studio."""
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


def chat(messages: list[dict], stream: bool = False):
    """Chat completion. Returns the full text (stream=False) or a token generator."""
    resp = client.chat.completions.create(
        model=cfg.CHAT_MODEL,
        messages=messages,
        temperature=0.2,
        stream=stream,
    )
    if not stream:
        return resp.choices[0].message.content or ""

    def token_stream():
        for chunk in resp:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    return token_stream()

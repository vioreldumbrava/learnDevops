"""Runtime configuration from environment variables (12-factor)."""
import os


class Config:
    # OpenAI-compatible endpoint. Works for BOTH backends:
    #   Ollama    -> http://ollama:11434/v1
    #   LM Studio -> http://host.docker.internal:1234/v1  (LM Studio's local server)
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://ollama:11434/v1")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "not-needed-for-local")

    CHAT_MODEL = os.getenv("CHAT_MODEL", "llama3.2:3b")
    EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

    QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
    QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "dojo_docs")

    # Comma-separated roots to index (markdown). In Compose the repo is mounted at /repo.
    DOCS_PATHS = os.getenv("DOCS_PATHS", "/repo/docs,/repo/labs,/repo/README.md")

    TOP_K = int(os.getenv("TOP_K", "4"))
    # Over-fetch this many candidates, then MMR-rerank down to TOP_K for relevance
    # + diversity. MMR_LAMBDA: 1.0 = pure relevance, 0.0 = pure diversity.
    FETCH_K = int(os.getenv("FETCH_K", "12"))
    MMR_LAMBDA = float(os.getenv("MMR_LAMBDA", "0.6"))
    # Conversation memory: how many prior turns to include in the prompt.
    HISTORY_TURNS = int(os.getenv("HISTORY_TURNS", "4"))
    # Retrieval grounding: if the best match is below this cosine score, answer
    # "I don't know" instead of hallucinating.
    MIN_SCORE = float(os.getenv("MIN_SCORE", "0.35"))

    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "900"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))

    REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "60"))
    PORT = int(os.getenv("PORT", "8000"))


cfg = Config()

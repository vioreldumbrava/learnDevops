# syntax=docker/dockerfile:1
# Python twin of app/api/Dockerfile. Different base (slim, not distroless — the
# Python runtime needs an interpreter + libs), same principles: deps cached in
# their own layer, runs as a non-root user, one image with two entrypoints (the
# worker Compose service overrides the command, exactly like the Go image).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install deps first for layer caching (edits to app/ don't re-install).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Non-root (matches the Go image's USER nonroot).
RUN useradd -u 10001 -m appuser
USER appuser

EXPOSE 8080
# Default entrypoint is the API on :8080 (same port as the Go api, so it's a
# drop-in). The worker service overrides this with:  python -m app.worker
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

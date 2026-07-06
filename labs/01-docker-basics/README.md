# Lab 01 — Docker basics: images, containers, layers

**Maps to:** original §1 · **Milestone:** 1

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

## Concept

- An **image** is a packaged, read-only filesystem + metadata (how to start it).
- A **container** is a running (or stopped) instance of an image.
- A **layer** is one filesystem step from the Dockerfile; layers are cached and shared.

## What you'll do

Build the Go API image and run it as a container — before any Compose, database, or
orchestration. The API is designed to boot even without its database (the DB connection is
lazy), so it's perfect for a first run.

## Steps

```powershell
# Build an image from app/api/Dockerfile (context = app/api)
docker build -t devops-dojo/api ./app/api

# See the image and its size
docker images devops-dojo/api

# Run it; the API listens on 8080
docker run --rm -p 8080:8080 devops-dojo/api
```

In a second terminal:

```powershell
curl http://localhost:8080/healthz
```

Stop the container with `Ctrl+C`. Now inspect the layers:

```powershell
docker history devops-dojo/api
docker ps -a
```

## How it works

The Dockerfile is **multi-stage**: a big `golang:1.25` stage compiles a static binary, then
only that binary is copied into a tiny `distroless` final image. `docker history` shows the
final image is just a couple of layers — no compiler, no shell. `--rm` deletes the
container when it exits so stopped containers don't pile up.

## Exercise

Run the worker entrypoint from the same image instead of the API:

```powershell
docker run --rm devops-dojo/api /worker
```

It will start, fail to reach Redis (none is running), and you'll see it retry — that's
expected here. Stop it with `Ctrl+C`.

## Checkpoint

- ✅ `docker images devops-dojo/api` shows an image well under ~30 MB.
- ✅ `curl http://localhost:8080/healthz` returns `{"status":"ok"}`.
- ✅ `docker history` shows the final image has only a few small layers.

## Common failures

- Port 8080 already in use → stop whatever owns it, or map a different host port: `-p 8081:8080`.
- `curl` not found → use your browser, or `Invoke-WebRequest http://localhost:8080/healthz`.

➡️ Next: [Lab 02 — Containerize the API](../02-containerize-api/)

# Lab 02 — Containerize the API: multi-stage, distroless, non-root

**Maps to:** original §2–3 · **Milestone:** 1

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

## Concept

A good production image is **small**, **secure**, and **reproducible**:
- **Multi-stage build** — compile in a fat toolchain image, ship only the result.
- **Distroless / non-root** — no shell, no package manager, runs as an unprivileged user,
  so a compromised process has almost nothing to work with.
- **Layer ordering for cache** — copy `go.mod`/`go.sum` and download deps *before* copying
  source, so dependency layers stay cached across code changes.

## What you'll do

Read [app/api/Dockerfile](../../app/api/Dockerfile), then prove the security and size
properties of the image you built in lab 01.

## Steps

```powershell
# Build (re-using lab 01's image name)
docker build -t devops-dojo/api ./app/api

# 1. It's tiny — compare to the ~800 MB golang build image
docker images devops-dojo/api

# 2. It's non-root and has no shell: this MUST fail
docker image inspect --format '{{.Config.User}}' devops-dojo/api
docker run --rm --entrypoint sh devops-dojo/api -c "whoami"

# 3. Rebuild after a no-op change and watch dependency layers come from cache
docker build -t devops-dojo/api ./app/api
```

## How it works

The final stage is `gcr.io/distroless/static-debian12:nonroot`. There is no `/bin/sh`, so
step 2 errors — that's the point: an attacker who lands in the container can't spawn a
shell. `USER 65532:65532` selects distroless's numeric non-root identity. The numeric form
also lets Kubernetes verify `runAsNonRoot` before starting the container. Because
`COPY go.mod go.sum` + `go mod download` happen before `COPY . .`, editing a `.go` file
only rebuilds the compile layer, not the dependency download (step 3 is fast).

### Bind mounts vs COPY

`COPY` **bakes** files into the image (immutable, what you ship). A **bind mount**
(`-v host:container`) maps a host folder into a running container live — great for
development, where you want edits to appear instantly. You'll use bind mounts for the
frontend dev server in lab 05.

## Exercise

Add a label to the final stage of the Dockerfile (e.g.
`LABEL org.opencontainers.image.source="devops-dojo"`), rebuild, and find it with:

```powershell
docker inspect --format '{{ index .Config.Labels \"org.opencontainers.image.source\" }}' devops-dojo/api
```

## Checkpoint

- ✅ Image inspection reports `65532:65532`, not root or a named user.
- ✅ The image is a few tens of MB, not hundreds.
- ✅ `--entrypoint sh ...` fails (no shell) — distroless confirmed.
- ✅ A second build reuses cached dependency layers.

## Common failures

- Build is slow every time → you changed something above the `COPY go.mod` line, busting the cache.
- `exec ... "sh": executable file not found` → expected; that's the distroless proof.

➡️ Next: [Lab 03 — Containerize the frontend](../03-containerize-frontend/)

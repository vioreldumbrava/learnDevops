# Lab 13 — Image registry: tags, push, SBOM

**Maps to:** original §13 · **Milestone:** 2

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

## Concept

A **registry** stores and serves container images. You **tag** an image with a
registry/repo/version, `push` it, and later `pull` it — so servers run a known artifact
instead of rebuilding from source. A tag (`:0.1.0`) is a movable label; a **digest**
(`@sha256:...`) is immutable. An **SBOM** (Software Bill of Materials) lists what's inside an
image, for auditing and vulnerability tracking.

## What you'll do

Push to a **local** registry (offline practice), then to **GHCR**, and inspect an image's
contents.

## Steps — local registry

```powershell
docker run -d -p 5000:5000 --name registry registry:2

docker build -t devops-dojo/api ./app/api
docker tag devops-dojo/api localhost:5000/dojo/api:0.1.0
docker push localhost:5000/dojo/api:0.1.0
docker pull localhost:5000/dojo/api:0.1.0

# See the digest (immutable identity)
docker images --digests localhost:5000/dojo/api
```

## Steps — GitHub Container Registry (GHCR)

```powershell
# Create a Personal Access Token (classic) with write:packages, then:
$env:CR_PAT | docker login ghcr.io -u <your-github-username> --password-stdin

docker tag devops-dojo/api ghcr.io/<owner>/<repo>/api:0.1.0
docker push ghcr.io/<owner>/<repo>/api:0.1.0
```

> In practice you rarely push by hand — the CI pipeline (lab 15) does it on every push to
> main and on tags. This lab is to understand what CI is automating.

## Steps — SBOM & scan

```powershell
docker scout sbom devops-dojo/api           # what's inside (or: syft devops-dojo/api)
docker scout quickview devops-dojo/api        # vulnerability summary
```

## How it works

Image names are `registry/repository:tag`. With no registry prefix, Docker assumes Docker
Hub. `localhost:5000/...` targets your local `registry:2`; `ghcr.io/owner/repo/...` targets
GHCR. The CI workflow ([.github/workflows/ci.yml](../../.github/workflows/ci.yml)) builds
with `docker/build-push-action` (with `sbom: true`), tagging by branch, semver, and git SHA
via `docker/metadata-action`.

## Exercise

Tag the same image two ways (`:0.1.0` and `:latest`), push both to the local registry, and
confirm with `docker images --digests` that they share **one digest** — proof that tags are
just labels pointing at the same immutable image.

## Checkpoint

- ✅ You pushed and pulled an image from `localhost:5000`.
- ✅ You can explain tag vs digest.
- ✅ `docker scout quickview` (or Trivy) prints a vulnerability summary for the API image.

## Common failures

- `http: server gave HTTP response to HTTPS client` when using a remote registry → local
  `registry:2` is insecure; that's fine on localhost. Real registries use TLS.
- GHCR push denied → your token lacks `write:packages`, or the image name has uppercase
  (must be lowercase).

Cleanup: `docker rm -f registry`.

➡️ Next: [Lab 14 — Artifact repository](../14-artifact-repository/)

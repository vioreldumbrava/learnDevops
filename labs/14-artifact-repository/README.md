# Lab 14 — Artifact repository (Nexus)

**Maps to:** original §14 · **Milestone:** 2 · *optional, heavy*

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

## Concept

A plain registry stores images. An **artifact repository manager** (Nexus, Artifactory)
stores *many* artifact types — container images, npm/Go/Maven packages, raw files — with
users, permissions, retention policies, and proxy/caching of upstream registries. It's the
central "shelf" a CI pipeline publishes build outputs to.

## What you'll do

Run Sonatype Nexus 3 locally, then host both a raw artifact and a Docker image in it.

> ⚠️ Nexus is heavy (~1 GB+ RAM, slow first boot). It's isolated in its own overlay so the
> rest of the stack stays light. Give Docker Desktop enough memory.

## Steps

```powershell
docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.nexus.yaml up -d nexus

# First-boot admin password:
docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.nexus.yaml exec nexus cat /nexus-data/admin.password
```

Open <http://localhost:8081>, sign in as `admin` with that password, and complete setup. Then:

1. **Raw repo:** create a `hosted / raw` repository (e.g. `dojo-artifacts`) and upload a
   build output — for example zip the frontend build and upload it:
   ```powershell
   docker build -t devops-dojo/frontend ./app/frontend   # produces dist inside the image
   # (or upload the SBOM / a generated report — anything that is a build output)
   ```
2. **Docker repo:** create a `hosted / docker` repository with HTTP connector `8085`, then:
   ```powershell
   docker login localhost:8085                    # admin + your password
   docker tag devops-dojo/api localhost:8085/dojo/api:0.1.0
   docker push localhost:8085/dojo/api:0.1.0
   ```

## How it works

Nexus exposes repositories over HTTP: the web UI/browse on `8081`, and a dedicated connector
port (`8085`) that speaks the Docker registry protocol. Compared to the plain `registry:2`
from lab 13, Nexus adds accounts, roles, cleanup policies, and can also **proxy** Docker
Hub/npm/Go to cache upstream artifacts for your team.

## Exercise

Create a **cleanup policy** (delete images older than N days or keep only the last N) and
attach it to your Docker repo. Retention is a core reason teams use a repository manager
rather than a bare registry.

## Checkpoint

- ✅ Nexus UI reachable at :8081 and you're logged in.
- ✅ You pushed an image to the Nexus Docker repo on :8085 (or uploaded a raw artifact).
- ✅ You can name two things Nexus/Artifactory add over a plain registry.

## Common failures

- Stuck on the loading screen → Nexus is still starting; watch `logs -f nexus` (first boot
  takes minutes).
- Docker push to :8085 fails → the hosted Docker repo/connector isn't created yet, or you
  didn't `docker login localhost:8085`.

Cleanup (frees the volume): `docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.nexus.yaml down -v`.

➡️ Next: [Lab 15 — CI/CD with GitHub Actions](../15-cicd/)

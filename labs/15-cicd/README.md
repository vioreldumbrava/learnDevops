# Lab 15 — CI/CD with GitHub Actions

**Maps to:** original §12 · **Milestone:** 2

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

## Concept

**CI** (Continuous Integration) runs your build, tests, and scans automatically on every
change. **CD** (Continuous Delivery) publishes the artifacts (images) and can deploy them.
The pipeline is the single most valuable automation in DevOps: it turns "works on my machine"
into "verified and shippable on every commit."

## What you'll do

Push the repo to GitHub and watch the pipeline build, test, scan, and publish images to GHCR.

## Steps

```powershell
# Create an empty GitHub repo, then from the repo root:
git remote add origin https://github.com/<owner>/<repo>.git
git push -u origin master        # or: git branch -M main; git push -u origin main
```

- Open the repo's **Actions** tab and watch the `CI` workflow run.
- After a run on `main`/`master`, open **Packages** — `api` and `frontend` images are
  published to GHCR.
- Open a **pull request** with a small change: CI builds, tests, and scans but does **not**
  push images (guard: `push: ${{ github.event_name != 'pull_request' }}`).

Optional — run it locally with [`act`](https://github.com/nektos/act):

```powershell
act pull_request
```

## How it works

[.github/workflows/ci.yml](../../.github/workflows/ci.yml) has two jobs:

1. **test** — `go vet` + `go test`, `npm ci` + `npm run build`, `docker compose config`
   validation, and a Trivy filesystem scan of dependencies.
2. **build** — logs in to GHCR with the built-in `GITHUB_TOKEN`, builds both images with
   Buildx, tags them via `docker/metadata-action` (branch, semver, SHA), attaches an **SBOM**
   and provenance, pushes on non-PR events, and runs a Trivy scan of the published API image
   by **digest**.

Triggers: pushes to `main`/`master`, version tags (`v*`), pull requests, and manual dispatch.

## Exercise

Make CI **gate** on vulnerabilities: change the Trivy steps' `exit-code: "0"` to `"1"`. Push
a branch and see the job fail if any CRITICAL/HIGH (fixable) vulnerabilities exist — then
decide whether to bump a base image or add an ignore policy. This is the build-vs-security
trade-off teams tune constantly.

## Checkpoint

- ✅ A green CI run appears in the Actions tab.
- ✅ `api` and `frontend` packages show up under the repo's Packages after a push to main.
- ✅ On a PR, images are built + scanned but not pushed.

## Common failures

- `denied: permission_denied` pushing to GHCR → the workflow needs `permissions: packages:
  write` (it has it); also check that Actions are allowed to write packages in repo settings.
- Go/Node version errors → the workflow pins Go 1.25 / Node 24 to match the app.

➡️ Next: [Lab 16 — Infrastructure as Code (Terraform)](../16-terraform/)

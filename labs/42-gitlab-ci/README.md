# Lab 42 — GitLab CI: translate the pipeline (optional)

**Maps to:** deepens lab 15 · **Milestone:** 4 — Operate & Automate · **optional, EU-market recommended**

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

## Concept

A huge share of European companies run **GitLab**, and "we use GitLab CI" filters out
candidates who only know Actions. The good news: CI concepts are portable — triggers, jobs,
containers, caching, artifacts, publish-vs-PR policy. What changes is the dialect. Being able
to *translate* a pipeline between systems is itself the skill interviewers probe ("we're
migrating from X to Y" is a perennial project).

The mapping to internalize:

| GitHub Actions | GitLab CI |
|----------------|-----------|
| workflow file per trigger | one `.gitlab-ci.yml`, `workflow:rules` decide when |
| job + `needs:` | job + `stage:` (or `needs:` for DAGs) |
| `steps` with `uses:` actions | `script:` lines in the job's own `image:` |
| marketplace actions | container images + `include:`/CI components |
| `GITHUB_TOKEN` → GHCR | `$CI_JOB_TOKEN` → built-in registry (`$CI_REGISTRY_IMAGE`) |
| `if: github.event_name != 'pull_request'` | `rules:` with `$CI_PIPELINE_SOURCE` |
| runner has Docker | `docker:dind` as a `service` |

## What you'll do

Mirror this repo to gitlab.com (free), run
[.gitlab-ci.yml](../../.gitlab-ci.yml) — the line-for-line translation of
[.github/workflows/ci.yml](../../.github/workflows/ci.yml) — and compare the two side by side.

## Steps

### 1. Mirror the repo

Create an empty project on gitlab.com (no README), then push this repo to it as a second
remote — same history, two homes:

```powershell
git remote add gitlab https://gitlab.com/<you>/devops-dojo.git
git push gitlab master
```

### 2. Watch the pipeline

GitLab picks up `.gitlab-ci.yml` from the repo root automatically — no enabling step. Open
**Build → Pipelines**: four `test` jobs run in parallel (Go, frontend, compose validation,
Trivy), then `build-publish` builds both images and pushes them to the project's **built-in
container registry** (**Deploy → Container Registry** — no PAT/token setup, `$CI_JOB_TOKEN`
just works; compare that with the GHCR login dance).

### 3. Prove the MR policy

```powershell
git switch -c lab42/mr-test
# any small change
git commit -am "test: gitlab MR pipeline"; git push gitlab lab42/mr-test
```

Open a merge request on GitLab: the pipeline now runs `build-mr` (build, **no push**) — the
same publish policy as the GitHub workflow, expressed with `rules:` instead of `if:`. Merge
it and watch `build-publish` fire on the default branch.

### 4. Read the translation side by side

Open both files in a split. For every block in the GitHub workflow, find its GitLab twin:
the two-tier Trivy policy, the tag-by-git-ref logic (`$CI_COMMIT_TAG` fallback to short
SHA), the dind service standing in for the runner's Docker, and `workflow:rules` preventing
the classic duplicate branch+MR pipelines. Everything you learned in labs 15/41 transferred
— only syntax changed.

## How it works

- **Stages vs needs:** GitLab's default model is sequential stages whose jobs run in
  parallel; `needs:` exists for DAG-style pipelines when stages are too coarse.
- **Every job is a container:** there's no "setup-go action" — you pick `image: golang:1.25`
  and it's set up. That's why GitLab jobs feel closer to Dockerfiles than to Actions steps.
- **dind:** shared runners can't hand you their Docker socket, so `docker:dind` runs a
  Docker daemon *as a sidecar service* — the same Docker-outside-of-Docker trade-off you met
  with Jenkins in lab 24.
- **The registry is part of the product:** project-scoped registry, `$CI_JOB_TOKEN` auth,
  automatic cleanup policies. This "batteries included" philosophy vs GitHub's
  marketplace-of-actions is the honest comparison to make in interviews.

## Exercise

1. Port the `terraform` checks job from lab 39 (`fmt`/`validate` in a
   `hashicorp/terraform:1.10` image) into the `test` stage.
2. Add cosign keyless signing (lab 41): GitLab also issues OIDC ID tokens
   (`id_tokens:` with `aud: sigstore`) — translate the signing step and note what changed.
3. Set up a **scheduled pipeline** (Build → Pipeline schedules) running the `test` stage
   nightly — the GitLab equivalent of a `schedule:` trigger.

## Checkpoint

- ✅ The mirrored pipeline is green on gitlab.com and images exist in the project registry.
- ✅ An MR runs `build-mr` (no push); merging runs `build-publish` (push) — and you can
  point at the `rules:` making that happen.
- ✅ Given any block of `ci.yml`, you can say what it becomes in `.gitlab-ci.yml` (and vice
  versa) using the mapping table from memory.

## Common failures

- Pipeline doesn't start → the file must be exactly `.gitlab-ci.yml` at the repo root;
  check **CI/CD → Editor** which validates syntax in-browser.
- `docker: not found` / cannot connect to Docker daemon → the job is missing the
  `docker:27-dind` service or `DOCKER_TLS_CERTDIR` — dind is per-job here, not ambient.
- Two pipelines per push on MR branches → your edit removed the `workflow:rules` block;
  that's exactly the duplicate-pipeline problem it exists to solve.
- Trivy job fails immediately with an entrypoint error → the image's default entrypoint is
  `trivy` itself; the `entrypoint: [""]` override is required to run `script:` lines.
- Push rejected to the registry → free-tier registry needs the project to be your own (or
  Maintainer role) — `$CI_JOB_TOKEN` has project scope only.

➡️ You've completed Milestone 4. Next stop: [docs/INTERVIEW_PREP.md](../../docs/INTERVIEW_PREP.md)
— every lab in this milestone maps to a talk track there.

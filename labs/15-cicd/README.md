# Lab 15 — Secure CI/CD with GitHub Actions

**Tier:** core · **Milestone:** delivery

**Run from:** the **repo root** (`learnDevops/`). Every command and path below is relative to it.

## Concept

Continuous integration turns a commit into repeatable evidence: tests passed, configuration
rendered, vulnerabilities were evaluated, and artifacts are traceable. Continuous delivery
publishes immutable images without giving pull requests publishing credentials.

Workflow dependencies are code. Third-party actions are pinned to full commit SHAs—the only
immutable action reference—and a nearby version comment keeps upgrades reviewable. Dependabot
opens updates for Actions and application dependencies rather than silently tracking mutable
tags.

## What you'll do

Take a pull request through the repository's validation pipeline, merge it, then inspect two
published images with SBOMs, provenance attestations, vulnerability gates, and keyless
signatures. AWS authentication is introduced in lab 39; no AWS keys belong in this workflow.

## Steps

```powershell
# Create an empty GitHub repository, then from this repository root:
git remote add origin https://github.com/<owner>/<repo>.git
git branch -M main
git push -u origin main
```

Open a small branch and pull request. In the Actions run, verify these independent outcomes:

- Go, Python, Node, and operator tests/builds pass.
- Compose overlays, migrations, curriculum/docs, Helm rendering, workload security, and
  Terraform roots validate.
- Trivy reports HIGH findings and blocks unexcepted CRITICAL findings.
- Images build and scan in a read-only PR job; the privileged publish/sign job is absent.

Review [`ci.yml`](../../.github/workflows/ci.yml) before merging. Every `uses:` entry must be
`owner/action@<40-character-commit>` with a readable version comment. Review
[`dependabot.yml`](../../.github/dependabot.yml) to see how updates remain automated without
making runtime references mutable.

Merge the PR. The protected push path publishes `api` and `frontend` to GHCR. Capture the
immutable digest printed by each build and inspect it:

```powershell
docker buildx imagetools inspect ghcr.io/<owner>/<repo>/api@sha256:<digest>

cosign verify `
  --certificate-identity-regexp '^https://github.com/<owner>/<repo>/' `
  --certificate-oidc-issuer https://token.actions.githubusercontent.com `
  ghcr.io/<owner>/<repo>/api@sha256:<digest>
```

The workflow's `id-token: write` permission is used only for Sigstore keyless signing. It
does not expose an AWS credential and is unavailable to the PR publication path.

## How it works

- The top-level workflow permission is read-only. PR code runs in a job with only
  `contents: read`; it cannot request a package-write token or OIDC identity.
- A separate non-PR publish job receives only the package and OIDC permissions required for
  GHCR push and keyless signing. A PR can prove buildability but cannot publish a trusted
  artifact.
- Buildx attaches an SBOM (what is inside) and provenance (source/builder/process) to each
  image. Cosign signs the immutable digest using the workflow's short-lived OIDC identity.
- The security policy reports HIGH findings but fails on fixable, non-excepted CRITICAL
  findings. `.trivyignore` is a governed exception file, not a bin for unexplained CVEs.

## Exercise

1. Change one third-party action locally from its SHA to `@main`; run the curriculum/CI
   checks and explain why that reference can change without a repository diff. Revert it.
2. Introduce a harmless formatting failure and observe the relevant job fail; fix it in a
   second commit so the PR records diagnosis and recovery.
3. In the published image, identify one package from the SBOM and connect the provenance
   source revision to your merge commit.

## Checkpoint

- A PR runs all credential-free validation, builds images, and publishes nothing.
- A merge publishes both images by immutable digest with SBOM, provenance, and keyless
  signatures; manual `cosign verify` succeeds for the expected workflow identity.
- An unexcepted CRITICAL finding fails CI.
- Every third-party Action is full-SHA pinned and Dependabot covers GitHub Actions.
- You can distinguish SBOM, provenance, and signature in one sentence each.

## Common failures

- GHCR push denied → confirm job-level `packages: write` and repository package settings.
- Cosign token error → the publishing job needs `id-token: write`; do not replace it with a
  stored signing key for this GitHub path.
- Identity mismatch → inspect the certificate identity, then tighten the expected expression
  to your repository/workflow rather than accepting every signer.
- Dependabot update changes a SHA without a version comment → verify the upstream release,
  update the comment in the same review, and keep the SHA.

➡️ Next: [Lab 16 — Infrastructure as Code](../16-terraform/)

# Lab 41 — Supply-chain security: signing, verification, gating

**Maps to:** deepens labs 13/15/29 · **Milestone:** 4 — Operate & Automate · **Security**

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

## Concept

Since lab 15 your CI has produced **SBOMs** and **provenance** — but nothing *consumes* them,
nothing proves an image in the cluster actually came from your CI, and the Trivy scans were
report-only. This lab closes the loop with three mechanisms:

1. **Sign** — CI signs image *digests* with **cosign keyless**: no key to manage, the
   signature is bound to the workflow's OIDC identity (Fulcio issues a short-lived cert,
   the proof lands in the public Rekor transparency log).
2. **Verify** — **Kyverno** (lab 29) checks the signature *at admission*: an image from your
   registry without a valid signature from your CI doesn't get to run.
3. **Gate** — Trivy now **fails CI on CRITICAL** vulnerabilities (HIGH stays visible but
   non-blocking), with a governed exception file (`.trivyignore`).

The interview one-liner this lab buys you: *"my cluster only runs images that my CI built,
scanned, signed, and attested — and I can prove it from a public transparency log."*

## What you'll do

Read the CI changes, trigger a signed build, verify it by hand and then at admission, and
watch the CRITICAL gate work. Needs: lab 15 (CI → GHCR), lab 29 (Kyverno on kind).

## Steps

### 1. What changed in CI

Open [.github/workflows/ci.yml](../../.github/workflows/ci.yml) and find:

- `id-token: write` on the trusted publish job — permission to mint the OIDC token that *is* the
  signing identity.
- The `cosign sign --yes …@<digest>` steps — signing the **digest**, never the tag: tags can
  be re-pointed after signing, digests can't.
- The two-tier Trivy steps — `report HIGH+` (exit 0) next to `gate on CRITICAL` (exit 1,
  honoring [.trivyignore](../../.trivyignore)).

Push a commit to `master` and let CI publish + sign both images. If your fork uses a
different default branch, substitute that branch tag in the commands and fixture below.

### 2. Verify a signature by hand

```powershell
# install cosign (one binary), then:
cosign verify `
  --certificate-identity-regexp "^https://github.com/OWNER/REPO" `
  --certificate-oidc-issuer https://token.actions.githubusercontent.com `
  ghcr.io/owner/repo/api:master
```

Read the output: the certificate's identity is your **workflow**, not a person, and the
entry is logged in Rekor. Now try verifying with someone else's repo in the identity regexp
— it fails. That's the whole point: a signature means nothing without pinning *who* was
supposed to sign.

### 3. Enforce it at admission

Edit `OWNER/REPO` in the GitHub workflow identity and replace lowercase `owner/repo` in
[deploy/k8s/policies/verify-image-signatures.yaml](../../deploy/k8s/policies/verify-image-signatures.yaml)
and both `*-image-test-pod.yaml` fixtures beside it,
then on the kind cluster with Kyverno installed:

```powershell
kubectl apply -f deploy/k8s/policies/verify-image-signatures.yaml

# a signed image (from CI) admits fine:
kubectl create -f deploy/k8s/policies/signed-image-test-pod.yaml
kubectl -n devops-dojo delete pod signed-test

# now push an UNSIGNED image into your registry and try it:
docker pull busybox:1.36
docker tag busybox:1.36 ghcr.io/owner/repo/api:unsigned
docker push ghcr.io/owner/repo/api:unsigned
kubectl create -f deploy/k8s/policies/unsigned-image-test-pod.yaml
```

In `Audit` mode the pod runs but the violation appears in
`kubectl get policyreport -n devops-dojo` (same flow as lab 29). Flip
`validationFailureAction: Enforce`, delete the Audit-mode pod, re-apply, and retry —
admission now **rejects** the unsigned
image. Clean up the `:unsigned` tag from GHCR afterwards.

```powershell
kubectl -n devops-dojo delete pod unsigned-test --ignore-not-found
kubectl apply -f deploy/k8s/policies/verify-image-signatures.yaml
kubectl create -f deploy/k8s/policies/unsigned-image-test-pod.yaml
```

### 4. See the gate refuse a CRITICAL

You don't want to merge a vulnerable dependency just to test CI — prove the mechanics
locally instead, with the same tool and exit-code contract:

```powershell
trivy image --severity CRITICAL --ignore-unfixed --exit-code 1 postgres:12.0; echo "exit: $LASTEXITCODE"
trivy image --severity CRITICAL --ignore-unfixed --exit-code 1 postgres:16-alpine; echo "exit: $LASTEXITCODE"
```

An ancient image trips the gate (exit 1), your current base doesn't. The CI steps are exactly
this with `.trivyignore` layered on. Exception process: a CVE may be ignored **only** with a
justification comment and a revisit date — an unexplained entry should die in code review.

### 5. Consume the SBOM you've been producing

```powershell
docker buildx imagetools inspect ghcr.io/owner/repo/api:master --format "{{ json .SBOM }}" > sbom.json
trivy sbom sbom.json
```

This is how "do we ship log4j anywhere?" gets answered in minutes instead of days — you scan
the *inventory documents*, not every running system.

## How it works

- **Keyless chain:** the workflow's OIDC token → Fulcio exchanges it for a ~10-minute
  certificate naming the workflow identity → cosign signs with it → signature + cert are
  stored in the registry next to the image, and the event is appended to **Rekor** (public,
  append-only). Verification = check the cert chains to Fulcio, matches your expected
  identity/issuer, and appears in the log. No private key exists long enough to steal.
- **Why admission-time verification:** CI signing alone proves nothing if the cluster will
  run anything. Kyverno's `verifyImages` makes the *cluster* demand proof — and
  `mutateDigest: true` re-pins the pod to the verified digest so the tag can't be swapped
  after the check.
- **Why gate CRITICAL but not HIGH:** a gate that cries wolf gets bypassed. CRITICAL+fixable
  is a defensible "stop the line" bar; HIGH stays visible and becomes backlog. Tighten as
  hygiene improves — policy should follow reality, not aspiration.
- **SBOM vs provenance:** SBOM = *what's inside* (packages); provenance = *how it was built*
  (builder, source, workflow). Signature = *who vouches*. Three different questions.

## Exercise

1. **Jenkins parity (lab 24):** Jenkins has no ambient OIDC identity, so keyless doesn't
   apply — do it the classic way: `cosign generate-key-pair`, private key in Jenkins
   credentials, `cosign sign --key …` in the Jenkinsfile. Be able to contrast the two models
   (managed identity vs managed secret).
2. Add the **frontend** image to the CI gate (it's currently only scanned as part of the fs
   scan) — copy the api pattern.
3. Stretch: Kyverno can verify **attestations**, not just signatures — extend the policy to
   require a `https://spdx.dev/Document` (SBOM) attestation on admitted images.

## Checkpoint

- ✅ `cosign verify` passes for your CI-built image and fails for a wrong identity regexp.
- ✅ With Enforce on, an unsigned image from your own registry is rejected at admission —
  and you watched it happen.
- ✅ You can explain keyless signing (OIDC → Fulcio → Rekor) in three sentences without
  saying "magic".
- ✅ You know the repo's exception process for a CRITICAL finding you can't fix today.

## Common failures

- CI signing step fails with an OIDC/token error → the trusted publish job lost
  `id-token: write` (job-level `permissions:` replaces workflow-level — keep all three).
- `cosign verify` fails with certificate identity mismatch → your regexp doesn't match the
  workflow path/branch in the cert; inspect with `--certificate-identity-regexp ".*"` first,
  then tighten.
- Kyverno reports `failed to fetch image` / webhook timeouts → the Kyverno pods need egress
  to ghcr.io and rekor.sigstore.dev (check lab 28's NetworkPolicies if applied to
  kyverno's namespace, and kind's network).
- Everything admits even in Enforce → your pod's image doesn't match
  `imageReferences` (`ghcr.io/owner/repo/*` — lowercase, exact repo), so the rule never
  fired. `kubectl describe clusterpolicy verify-image-signatures` to confirm.
- Gate fails on a CVE with no released fix → `ignore-unfixed: true` already skips those; if
  it's fixable, bump the base image — that's the gate doing its job.

➡️ Next: [Lab 42 — GitLab CI](../42-gitlab-ci/)

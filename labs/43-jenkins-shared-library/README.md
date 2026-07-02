# Lab 43 — Jenkins deep-dive: Shared Library, webhooks, dynamic versioning

**Maps to:** deepens lab 24 · **Milestone:** 5 — Ecosystem breadth · *TWN Bootcamp Module 8*

## Concept

Lab 24 gave you *a* Jenkinsfile. Real Jenkins shops have *hundreds* — and three patterns keep
them sane, all of which interviewers probe:

1. **Shared Library** — common build logic (build, scan, push, version) extracted into a
   versioned Groovy library so fifty Jenkinsfiles don't copy-paste the same twenty lines.
   Change the Trivy policy once, every pipeline picks it up.
2. **Webhook triggers** — builds start when Git *pushes* to Jenkins, not when Jenkins polls
   Git. Polling wastes cycles and adds latency; webhooks are how production Jenkins works.
3. **Dynamic versioning** — the pipeline increments the app version, tags images with it, and
   commits the bump back. The classic gotcha: that commit triggers the pipeline again →
   infinite loop. GitHub Actions honors `[skip ci]` natively; **Jenkins does not** — you must
   guard yourself.

## What you'll do

Configure this repo's [jenkins-shared-library/](../../jenkins-shared-library/) as a Global
Pipeline Library, run the JSL-based pipeline ([Jenkinsfile](Jenkinsfile) in this folder — the
lab-24 pipeline rebuilt on library steps), and watch the version-bump commit land *without*
re-triggering the build.

## Steps

### 1. Start Jenkins (lab 24 setup)

```powershell
docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.jenkins.yaml up -d --build jenkins
```

(Rebuild matters: [plugins.txt](../../deploy/jenkins/plugins.txt) now includes the `github`
plugin for webhook triggers.)

### 2. Register the shared library

**Manage Jenkins → System → Global Trusted Pipeline Libraries → Add:**

| Field | Value |
|-------|-------|
| Name | `dojo-lib` |
| Default version | `master` |
| Retrieval method | Modern SCM → Git |
| Project Repository | your repo URL (same one the job uses) |
| Advanced → Library Path | `jenkins-shared-library/` |

*Library Path* is what lets the library live in a subfolder of this repo. In real teams the
library gets its **own repo** (that's the TWN original) — same config minus the path.

### 3. Create the pipeline job

**New Item → Pipeline** → *Pipeline script from SCM* → Git → your repo URL →
**Script Path: `labs/43-jenkins-shared-library/Jenkinsfile`** (monorepos routinely carry
several Jenkinsfiles — the Script Path field is how jobs pick theirs).

Add the push credential the last stage needs: **Manage Jenkins → Credentials → Add →
Username with password**, id `git-push-creds`, username = your GitHub user, password = a PAT
with `repo` write.

### 4. Build and watch the version flow

**Build Now.** The stage view runs: Guard → Bump version → Build images → Scan → Commit bump.
Then check:

```powershell
git pull
git log --oneline -1        # ci: bump version to 0.1.1 [ci skip]
cat VERSION                 # 0.1.1
```

**Build Now** again: the Guard stage sees `[ci skip]` in the latest commit and aborts the
build — that's the loop protection working. Push any real commit and the pipeline runs fully
again.

### 5. Webhook trigger (instead of polling)

A local Jenkins has no public URL, so GitHub can't reach it directly. Relay with
[smee.io](https://smee.io) (or ngrok):

```powershell
# one-time: create a channel on smee.io, then
npx smee-client --url https://smee.io/<your-channel> --target http://localhost:8088/github-webhook/
```

1. GitHub repo → **Settings → Webhooks → Add**: Payload URL = your smee channel, content type
   `application/json`, event: *Just the push event*.
2. Job → **Configure → Build Triggers → GitHub hook trigger for GITScm polling**.
3. Push a commit → the build starts within seconds, no polling.

No public relay available? Fallback: **Poll SCM** with a schedule like `H/2 * * * *` — worse
latency, same effect for the lab.

## How it works

- A shared library has a fixed layout: every file in
  [vars/](../../jenkins-shared-library/vars/) becomes a **global step** named after the file —
  `buildImage.groovy` gives every pipeline a `buildImage(...)` step. `@Library('dojo-lib') _`
  at the top of the [Jenkinsfile](Jenkinsfile) loads it.
- [bumpPatchVersion.groovy](../../jenkins-shared-library/vars/bumpPatchVersion.groovy) rewrites
  the root [VERSION](../../VERSION) file and returns the new value; images are tagged with it
  instead of `$BUILD_NUMBER` — the version now *means something* across systems.
- [commitVersionBump.groovy](../../jenkins-shared-library/vars/commitVersionBump.groovy)
  pushes the bump with `[ci skip]` in the message;
  [ciSkipRequested.groovy](../../jenkins-shared-library/vars/ciSkipRequested.groovy) checks
  the last commit for the marker and the Guard stage aborts the build if found. Note the
  credential handling: the PAT stays in a **shell** variable (`$GIT_TOKEN`), never
  interpolated into a Groovy string — interpolated secrets end up in build logs.
- Compare with the same problem solved in GitHub Actions
  ([ci.yml](../../.github/workflows/ci.yml)): Actions gets `[skip ci]` handling, checkout
  credentials, and marketplace steps for free; Jenkins gives you full control and makes you
  own each piece. That trade-off is the recurring theme of labs 15/24/42/43.

## Exercise

1. Add a `pushImage(name, tag, registry)` step to the library that logs in with a credential
   and pushes — then call it from the Jenkinsfile after Scan (re-use the `ghcr-creds` from
   lab 24's exercise).
2. Break the loop guard on purpose: remove `[ci skip]` from the commit message in
   `commitVersionBump.groovy`, push, and watch build → commit → build. Revert and explain in
   one sentence why the guard must check the *incoming* commit, not build state.

## Checkpoint

- ✅ The pipeline runs green using library steps (`buildImage`, `scanImage`, ...).
- ✅ `VERSION` increments and the bump commit appears in `git log` with `[ci skip]`.
- ✅ A build triggered by the bump commit aborts in the Guard stage; a real commit builds fully.
- ✅ (Webhook variant) a push starts the build without polling.
- ✅ You can explain why a shared library beats copy-pasted Jenkinsfiles — and name its cost
  (a shared dependency that can break fifty pipelines at once).

## Common failures

- `No such library dojo-lib` → the Global Pipeline Library isn't registered, name doesn't
  match `@Library('dojo-lib')`, or *Library Path* is missing so Jenkins looks for `vars/` at
  the repo root.
- `git push` rejected (auth) → `git-push-creds` missing or the PAT lacks `repo` write; check
  **Manage Jenkins → Credentials**.
- Build loop (pipeline keeps triggering itself) → the Guard stage was skipped or the bump
  commit lost its `[ci skip]` marker.
- Webhook shows red ✗ in GitHub → smee relay not running, or the target isn't
  `http://localhost:8088/github-webhook/` (trailing slash matters).

➡️ Back to the map: [docs/CURRICULUM.md](../../docs/CURRICULUM.md)

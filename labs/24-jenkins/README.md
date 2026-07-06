# Lab 24 — Self-hosted CI/CD with Jenkins

**Maps to:** original §12 (alternative to lab 15) · **Milestone:** 2 · *complement to GitHub Actions*

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

## Concept

Lab 15 used **GitHub Actions** — CI/CD **managed** by GitHub. **Jenkins** is the classic
**self-hosted** alternative: a server *you* run, secure, and extend with plugins. Same goal
(build → test → scan → publish), different model. Seeing both is valuable because real teams
choose between managed and self-hosted CI/CD all the time — and a huge amount of industry
infrastructure runs on Jenkins.

Key differences to feel:
- **Pipeline as code** lives in a `Jenkinsfile` (Groovy declarative) instead of YAML.
- **You** own uptime, plugins, credentials, and agents.
- **Agents & Docker-outside-of-Docker**: stages run in throwaway tool containers.

## What you'll do

Run Jenkins locally, point a Pipeline job at this repo's `Jenkinsfile`, and watch it build.

> ⚠️ Heavy, and it mounts the Docker socket (root-equivalent — same caveat as Promtail in
> lab 11; see lab 19). Local learning only.

## Steps

```powershell
docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.jenkins.yaml up -d --build jenkins

# Initial admin password:
docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.jenkins.yaml exec jenkins `
  cat /var/jenkins_home/secrets/initialAdminPassword
```

1. Open <http://localhost:8088>, unlock with that password, install suggested plugins, create
   an admin user.
2. **New Item → Pipeline** (or **Multibranch Pipeline**) → point it at this repo. For a plain
   Pipeline job choose *"Pipeline script from SCM"*, Git, your repo URL, script path
   `Jenkinsfile`.
3. **Build Now** and watch the stage view: Test (Go) → Build frontend → Build images → Scan.

Tear down: `docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.jenkins.yaml down -v`.

## How it works

- [deploy/jenkins/Dockerfile](../../deploy/jenkins/Dockerfile) is Jenkins LTS + the Docker CLI;
  [plugins.txt](../../deploy/jenkins/plugins.txt) pre-installs the pipeline/docker plugins.
- [compose.jenkins.yaml](../../deploy/compose/compose.jenkins.yaml) mounts the host Docker
  socket so pipeline steps can build images and run tool containers
  (**Docker-outside-of-Docker**).
- [Jenkinsfile](../../Jenkinsfile) is a declarative pipeline. The `Test` and `Build frontend`
  stages use `agent { docker { image '...' } }` — the Docker Pipeline plugin shares the
  workspace into those containers, so no host-path mounting is needed. `Build images` and
  `Scan` run on the Jenkins node using the mounted socket.

Compare it side by side with [.github/workflows/ci.yml](../../.github/workflows/ci.yml): same
stages, different tool and syntax.

## Exercise

Add real publishing: in Jenkins create a **username/password credential** (`ghcr-creds`), then
uncomment the `withCredentials` block in the `Push` stage of the `Jenkinsfile` to
`docker login` + `docker push` to GHCR on `main`. That's the "CD" half — and a good moment to
appreciate what Actions' `GITHUB_TOKEN` gave you for free.

## Checkpoint

- ✅ Jenkins is reachable at :8088 and you unlocked it.
- ✅ A Pipeline job runs the `Jenkinsfile` green through the Build/Scan stages.
- ✅ You can name two things Jenkins makes you own that GitHub Actions handled for you.

## Common failures

- `docker: not found` / permission denied in a stage → the socket isn't mounted or the
  container can't access it; this overlay runs Jenkins as root for exactly that reason.
- Job can't find `Jenkinsfile` → check the SCM path is `Jenkinsfile` at the repo root.
- First boot is slow → Jenkins is unpacking plugins; watch `logs -f jenkins`.

## Managed vs self-hosted — when to pick which

- **GitHub Actions (lab 15):** zero infra, great for GitHub-hosted repos, pay-per-minute.
- **Jenkins (this lab):** full control, runs anywhere (air-gapped/on-prem), huge plugin
  ecosystem — but you operate, patch, and secure it yourself.

➡️ Back to the map: [docs/CURRICULUM.md](../../docs/CURRICULUM.md)

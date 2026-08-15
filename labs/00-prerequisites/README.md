# Lab 00 — Prerequisites & repo tour

**Maps to:** — · **Milestone:** 1

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

> All commands run from the **repo root** (`learnDevops/`) in PowerShell.

## Concept

DevOps is the practice of shipping and operating software reliably: you package an app
(Docker), run its pieces together (Compose), give it a database, watch it (metrics/logs/
traces), automate its delivery (CI/CD), and run it in production (a server, then
Kubernetes). This course teaches each of those by doing them to one real app — **DevOps
Dojo** — the dashboard you're looking at, which tracks your own progress.

## What you'll do

Install the tools, verify them, and learn where everything lives.

## Steps

1. Install **Docker Desktop** and make sure it uses **Linux containers** (the default).
2. Verify the toolchain:

   ```powershell
   docker version
   docker compose version
   ```

3. Make this folder a git repository (needed for lab 15, CI/CD):

   ```powershell
   git init
   git add -A
   git commit -m "DevOps Dojo: initial import"
   ```

4. Create your local environment file:

   ```powershell
   copy .env.example .env
   ```

5. Tour the layout (read [docs/CURRICULUM.md](../../docs/CURRICULUM.md) and the
   [root README](../../README.md)). The two halves to internalize:
   - **App code:** `app/api` (Go), `app/frontend` (React), `db/migrations` (SQL).
   - **Ops code:** `deploy/` (Compose, Caddy, monitoring, k8s, terraform, ansible).

New to Linux shells? Skim [docs/LINUX_FOR_CONTAINERS.md](../../docs/LINUX_FOR_CONTAINERS.md);
you'll need it from lab 18 (servers) onward.

## How it works

Nothing is running yet. Docker Desktop gives you the `docker` and `docker compose` CLIs and
a Linux VM to run containers in. `.env` holds the values that change between machines and
environments (passwords, domains) so they never get hard-coded.

## Exercise

Open `.env` and change `POSTGRES_PASSWORD` to something of your own. (It's gitignored, so
it won't be committed.)

## Checkpoint

- ✅ `docker version` and `docker compose version` both print versions.
- ✅ A `.env` file exists in the repo root.
- ✅ `git status` works (you're in a git repo).

## Common failures

- "Cannot connect to the Docker daemon" → Docker Desktop isn't running.
- You're on Windows containers → switch to Linux containers in the Docker Desktop tray menu.

➡️ Next: [Git basics from Lab 38](../38-git-workflows/)

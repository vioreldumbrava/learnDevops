# Lab 03 — Containerize the frontend

**Maps to:** original §5 · **Milestone:** 1

## Concept

A single-page app has two phases: a **build** (Node + Vite compiles React/TypeScript into
static HTML/JS/CSS) and a **serve** (a web server hands those files to browsers). Multi-stage
keeps the heavy Node toolchain out of the final image — production ships a tiny Nginx image
with only the compiled `dist/`.

## What you'll do

Build the frontend image and run it on its own.

## Steps

```powershell
docker build -t devops-dojo/frontend ./app/frontend
docker images devops-dojo/frontend

docker run --rm -p 3000:80 devops-dojo/frontend
```

Open <http://localhost:3000>. Then check the two stages:

```powershell
docker history devops-dojo/frontend
```

Stop with `Ctrl+C`.

## How it works

Stage 1 (`node:24-alpine`) runs `npm install` + `npm run build`. Stage 2 (`nginx:alpine`)
copies `/app/dist` and the [nginx.conf](../../app/frontend/nginx.conf). Nginx serves the
SPA, falls back to `index.html` for client-side routes, and proxies `/api/*` to the `api`
service. Running standalone (no API yet), the dashboard **loads** but shows
"Couldn't reach the API" — proving the frontend and backend are independent containers.

## Exercise

`curl http://localhost:3000/healthz` — the Nginx config serves its own liveness endpoint.
Find where in `nginx.conf` that's defined and why a frontend container needs its own health
endpoint separate from the API's.

## Checkpoint

- ✅ <http://localhost:3000> renders the DevOps Dojo shell.
- ✅ `curl http://localhost:3000/healthz` returns `ok`.
- ✅ `docker history` shows the Node build tools are **not** in the final image.

## Common failures

- Blank page / 404s on refresh → the SPA fallback (`try_files ... /index.html`) is what
  prevents that; check `nginx.conf` if you changed it.
- `npm install` fails in the build → check `app/frontend/package.json` is valid.

➡️ Next: [Lab 04 — Docker Compose](../04-docker-compose/)

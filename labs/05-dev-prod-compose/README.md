# Lab 05 — Dev/prod Compose separation

**Maps to:** original §6 · **Milestone:** 1

## Concept

You want **the same app** in development and production, but configured differently: dev
favours fast feedback (hot reload, exposed databases); prod favours safety (a single public
entrypoint, TLS, restart policies). Compose solves this with **overlays** — a base file plus
`-f` override files merged left-to-right.

## What you'll do

Run the dev overlay (Vite hot reload) and the prod overlay (Caddy), and diff them.

## Steps

```powershell
# See what each stack resolves to
docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.dev.yaml config
docker compose --env-file .env -f deploy/compose/compose.yaml -f deploy/compose/compose.prod.yaml config

# DEV: Vite dev server with hot reload at http://localhost:5173
docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.dev.yaml up --build
```

With dev running, edit `app/frontend/src/App.tsx` (change the tagline text) and save — the
browser updates instantly, no rebuild. Stop with `Ctrl+C`, then:

```powershell
# PROD: behind Caddy at http://localhost (port 80)
docker compose --env-file .env -f deploy/compose/compose.yaml -f deploy/compose/compose.prod.yaml up -d --build
curl http://localhost/healthz
docker compose --env-file .env -f deploy/compose/compose.yaml -f deploy/compose/compose.prod.yaml down
```

## How it works

- **Dev overlay** replaces the frontend with a `node` container that bind-mounts the source
  and runs `npm run dev`; it also publishes Postgres/Redis on localhost for inspection. The
  `!override` / `!reset` YAML tags replace inherited values instead of merging them.
- **Prod overlay** adds `caddy`, the only service that publishes public ports (80/443). The
  app tier's host ports are bound to `127.0.0.1` in the base file, so on a server they're
  unreachable from the internet — Caddy reaches them by service name.

## Exercise

Run `config` for dev and prod side by side and list three concrete differences (which ports
are published, what the `frontend` service is, what extra service exists in prod).

## Checkpoint

- ✅ Editing `App.tsx` while the dev stack runs hot-reloads at :5173.
- ✅ The prod stack serves the app at `http://localhost` via Caddy.
- ✅ You can name the differences between the two merged configs.

## Common failures

- Hot reload not working → make sure you ran the **dev** overlay (5173), not the base (3000).
- Port 80 in use (IIS, Skype) → stop it or change Caddy's published port in the prod overlay.

➡️ Next: [Lab 06 — Database & migrations](../06-database-migrations/)

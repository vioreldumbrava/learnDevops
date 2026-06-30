# Lab 04 — Docker Compose: multi-service, DNS, networks, volumes

**Maps to:** original §4 · **Milestone:** 1

## Concept

Real apps are several containers that must start in order and talk to each other. **Compose**
declares them in one file: services share a network (and can reach each other **by service
name** as a DNS hostname), volumes persist data, `depends_on` orders startup, and one-shot
jobs (like migrations) can run to completion before others start.

## What you'll do

Bring the whole base stack up with one command and see the pieces cooperate.

## Steps

```powershell
# Build images and start everything (db, redis, migrate, api, worker, frontend)
docker compose -f deploy/compose/compose.yaml up -d --build

# Watch the graph: db becomes healthy -> migrate runs & exits 0 -> api/worker start
docker compose -f deploy/compose/compose.yaml ps

# The migrate one-shot's logs
docker compose -f deploy/compose/compose.yaml logs migrate

# The API answers (note: db/redis have NO host ports; only the app tier is published)
curl http://localhost:8080/api/steps

# Service-to-service DNS: connect to the db BY NAME from inside the network
docker compose -f deploy/compose/compose.yaml exec db psql -U dojo -d dojo -c "select count(*) from steps;"
```

Open <http://localhost:3000>, tick a lab complete, reload — it persists.

```powershell
docker compose -f deploy/compose/compose.yaml down
```

## How it works

- **Service DNS:** the API reaches Postgres at `db:5432` and Redis at `redis:6379` because
  Compose puts them on one network where the service name resolves.
- **Ordering:** `api` has `depends_on` with `migrate: service_completed_successfully`, so
  migrations finish before the API starts. `db`/`redis` use `service_healthy`.
- **Volumes:** `db-data` and `redis-data` keep state across restarts. `down` keeps volumes;
  `down -v` deletes them (a clean slate).

## Exercise

Stop with `down` (keep volumes), then `up -d` again and re-open the dashboard. Your ticked
lab is still complete — the `db-data` volume survived. Now `down -v` and `up -d`: progress
resets. That contrast *is* the difference between ephemeral containers and persistent volumes.

## Checkpoint

- ✅ `ps` shows db/redis/api/frontend running (migrate `Exited (0)`).
- ✅ `curl .../api/steps` returns a JSON array of 24 steps.
- ✅ Toggling a lab at :3000 persists across reload (and across `down`/`up`, but not `down -v`).

## Common failures

- API restarts in a loop → migrations didn't run; check `logs migrate` and that `db` is healthy.
- Port 3000/8080 in use → free it or edit the published ports.

➡️ Next: [Lab 05 — Dev/prod Compose separation](../05-dev-prod-compose/)

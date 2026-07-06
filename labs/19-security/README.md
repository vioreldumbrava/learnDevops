# Lab 19 — Security hardening

**Maps to:** original §17 · **Milestone:** 3

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

## Concept

Reduce what a compromised container can do — **least privilege** at every layer:
- Small, **non-root**, shell-less images (already done: distroless API).
- **`no-new-privileges`** so a process can't escalate via setuid binaries.
- **Drop all Linux capabilities** the app doesn't need.
- **Read-only root filesystem** + explicit `tmpfs` for scratch paths.
- **Keep data ports private** (only the reverse proxy is public).
- **Scan** images for known vulnerabilities; **manage secrets** properly.

## What you'll do

Apply the hardening overlay and verify the constraints are really in effect.

## Steps

```powershell
docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.hardening.yaml up -d --build

# Prove the constraints are applied
docker inspect devops-dojo-api-1 --format 'ReadonlyRootfs={{.HostConfig.ReadonlyRootfs}}  CapDrop={{.HostConfig.CapDrop}}  SecurityOpt={{.HostConfig.SecurityOpt}}'
docker inspect devops-dojo-frontend-1 --format 'ReadonlyRootfs={{.HostConfig.ReadonlyRootfs}}  SecurityOpt={{.HostConfig.SecurityOpt}}'

# Scan an image for known CVEs
docker scout quickview devops-dojo/api:dev
# or: docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image devops-dojo/api:dev

docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.hardening.yaml down
```

## How it works

[compose.hardening.yaml](../../deploy/compose/compose.hardening.yaml) adds
`security_opt: [no-new-privileges:true]` everywhere, `cap_drop: [ALL]` + `read_only` +
`tmpfs:/tmp` on the Go services, and a read-only Nginx with `tmpfs` for its cache/run/tmp
paths. Postgres/Redis keep a writable data volume (they need it) but still get
`no-new-privileges`. Two design choices already baked in from earlier labs: the API image is
distroless/non-root, and app/DB host ports bind to `127.0.0.1` (public exposure only via
Caddy).

**Secrets:** `.env` is fine for learning and is gitignored, but real deployments should use a
secret manager (Docker/Swarm secrets, Vault, AWS Secrets Manager, or K8s Secrets from an
external store) and rotate credentials.

## Exercise

Try to break out: exec a shell in the hardened API (`docker exec -it devops-dojo-api-1 sh`) —
it fails (no shell, distroless). Then try writing a file in the frontend
(`docker exec devops-dojo-frontend-1 sh -c 'touch /etc/x'`) — it fails (read-only rootfs).
Feeling the walls is the lesson.

## Checkpoint

- ✅ `docker inspect` shows `ReadonlyRootfs=true`, `CapDrop=[ALL]` (api), `no-new-privileges`.
- ✅ The hardened stack still serves normally (health checks green).
- ✅ A vulnerability scan runs and you can read its summary.

## Common failures

- A service crash-loops after hardening → it needs a writable path; add a `tmpfs` mount for
  it (that's why Nginx has three) rather than disabling read-only.

➡️ Next: [Lab 20 — Load testing](../20-load-testing/)

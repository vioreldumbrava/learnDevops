# Dojo Operator 🥋⚙️ — build your own Kubernetes operator (Go)

The third DevOps Dojo project. Projects one and two made you a *user* of
operators — cert-manager issued your certificates, KEDA scaled your worker,
ArgoCD reconciled your deployments, and you never saw how. This project removes
the magic: you build **`dojo-operator`**, a real operator that manages
**scheduled Postgres backups** for the Dojo's own database through a custom
resource:

```yaml
apiVersion: dojo.dev/v1alpha1
kind: DojoBackup
metadata: { name: dojo-db, namespace: devops-dojo }
spec:
  schedule: "*/2 * * * *"     # cron
  retention: 3                # keep newest N dumps
  database:
    host: db
    name: dojo
    user: dojo
    passwordSecret: { name: dojo-secrets, key: POSTGRES_PASSWORD }
```

Apply that, and the operator creates a PVC + CronJob running `pg_dump` (lab 07's
skill, now automated by *your* software), prunes old dumps, reports status and
conditions, survives tampering, and blocks deletion while a backup is running.

**Why this deepens your DevOps knowledge:** every concept the Kubernetes
deep-dive used from the outside is built here from the inside — the
reconcile loop (what "GitOps-style convergence" actually is), CRDs and API
schema validation, ownerReferences and garbage collection, finalizers (and why
namespaces get stuck Terminating), the /status subresource, RBAC for software
instead of humans, events, and controller metrics. "I wrote an operator" is a
sentence very few junior/mid candidates can say and defend.

## Architecture (one reconcile pass)

```
DojoBackup (spec)          you edit this
      │ watch
      ▼
┌───────────────┐   creates/converges   ┌────────────┐     schedule     ┌─────┐
│  dojo-operator │ ────────────────────▶ │  CronJob   │ ───────────────▶ │ Job │
│  Reconcile()   │ ────────────────────▶ │  PVC       │                  └──┬──┘
└───────┬───────┘                        └────────────┘        pg_dump      │
        │ writes                                              + prune to    ▼
        ▼                                                     retention  /backups
DojoBackup (status)        you read this                                (the PVC)
```

## Prerequisites

- The kind cluster with the Dojo app deployed (**lab 22**: `deploy/k8s/base`),
  so there is a database to back up.
- **Go 1.23+ on your machine** (`winget install GoLang.Go`) — this project is
  the one place you run Go directly (`go run`, `go test`); everything else can
  stay in containers.
- Docker (for building the operator image in lab 05).

## Quick start

```powershell
# from the repo root
cd dojo-operator
kubectl apply -f config/crd/dojo.dev_dojobackups.yaml
kubectl apply -f config/samples/backup.yaml
go run ./cmd        # the operator, running on your laptop against the cluster
# in another terminal:
kubectl -n devops-dojo get djb,cronjob,pvc
```

## The labs (in order — each ~30–45 min)

| Lab | You learn | The "aha" |
|-----|-----------|-----------|
| [01 — CRDs: the API half](labs/01-crd-the-api-half/) | a CRD is a schema'd REST endpoint, no code needed | apply a CR and… nothing happens: data ≠ behavior |
| [02 — The reconcile loop](labs/02-reconcile-loop/) | level-based convergence, watches, the cache | delete the operator's CronJob — it resurrects |
| [03 — Status, conditions & events](labs/03-status-conditions-events/) | /status subresource, conditions, events | `kubectl wait --for=condition=Ready djb/dojo-db` works on YOUR type |
| [04 — Ownership, GC & finalizers](labs/04-ownership-gc-finalizers/) | ownerReferences, cascading delete, finalizers | you create (and fix) a resource stuck in Terminating |
| [05 — RBAC & in-cluster deploy](labs/05-rbac-and-deploy/) | ServiceAccount identity, least privilege, distroless ship | the operator can't read the secret it schedules backups with |
| [06 — Tests & CI](labs/06-testing-and-ci/) | fake-client unit tests, what to assert about a controller | drift-convergence as a unit test |

Every lab follows the repo's standard template and states its **Run from**
directory. After lab 06, the [interview Q&A](../docs/INTERVIEW_PREP.md) has an
operator section — rehearse it.

## Repo layout

```
cmd/main.go                        manager: cache, queue, metrics, probes, leader election
api/v1alpha1/                      the API types (spec/status) + deepcopy
internal/controller/               Reconcile() + its unit tests
config/crd/                        the CustomResourceDefinition (hand-annotated)
config/rbac/                       namespace, ServiceAccount, ClusterRole(+Binding)
config/manager/deployment.yaml     runs the operator in-cluster (lab 05)
config/samples/backup.yaml         DojoBackup for the Dojo's own db
Dockerfile                         multi-stage -> distroless (same as app/api)
```

## What this is not (scope, stated honestly)

- Not HA by default (1 replica; `--leader-elect` is the lab 05 exercise).
- No webhooks (validation lives in the CRD schema; conversion/defaulting
  webhooks are the natural "where to go next").
- Backups land on a PVC, not S3 — swapping the CronJob's pod to `aws s3 cp`
  is deliberate exercise material (ties into lab 40).

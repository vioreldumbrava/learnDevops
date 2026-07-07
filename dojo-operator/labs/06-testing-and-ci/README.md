# Operator Lab 06 — Tests & CI

**Maps to:** deepens labs 15/41 · **Project:** dojo-operator · **Platform**

**Run from:** the [`dojo-operator/`](../../) folder. Needs Go 1.23+ (or use the docker variant shown).

## Concept

What do you *assert* about a controller? Not "it called the API" — you assert
the **converged end state**: given this CR, after Reconcile the cluster
contains this CronJob with this owner, this status, this finalizer. The
**fake client** makes that cheap: an in-memory stand-in for the API server, no
cluster, milliseconds per test. The trade-off is honesty: the fake client
doesn't run garbage collection, admission, or real CronJob scheduling — so unit
tests prove *your logic*, and labs 02–05 proved *the integration*. You need
both layers, and you should be able to say why.

## What you'll do

Run the test suite, map each test to the behavior you witnessed live in labs
02–04, then extend it.

## Steps

```powershell
# Run the suite (local Go):
go vet ./...
go test ./... -v

# …or containerized, same as the main project's CI habit:
docker run --rm -v ${PWD}:/w -w /w golang:1.25 go test ./... -v
```

Expected: 4 passing tests. Now read
[internal/controller/dojobackup_controller_test.go](../../internal/controller/dojobackup_controller_test.go)
and match each test to what you already saw live:

| Test | The live moment it pins down |
|------|------------------------------|
| `TestReconcileCreatesCronJobAndPVC` | lab 02 step 2 — children appear, owned, Ready=True |
| `TestReconcileConvergesDriftedCronJob` | lab 02 step 4 — tampering snaps back |
| `TestReconcilePropagatesSuspend` | spec is the only input the robot obeys |
| `TestDeletionBlockedWhileJobRuns` | lab 04 steps 5–6 — Terminating until the job ends |

The drift test is the one to remember: **convergence as a unit test** is the
single strongest assertion you can make about a controller, and most people
don't know to write it.

CI: the root [ci.yml](../../../.github/workflows/ci.yml) has an `operator` job
running exactly these commands on every push/PR — your operator is gated like
any other service in the monorepo.

## How it works

`fake.NewClientBuilder().WithScheme(...).WithObjects(cr)` builds the in-memory
"cluster"; `WithStatusSubresource(&DojoBackup{}, &Job{})` teaches it that
status writes for those types go through a subresource — mirroring the real
server, where a plain `Update` **silently drops** status changes (a bug this
suite genuinely caught during development: setting a Job's status via `Update`
persisted nothing). Tests then drive `Reconcile` directly — no
manager, no watches, no queue — because those are controller-runtime's job,
already tested upstream; *your* code is the function. `reconcileTwice` mirrors
a real-world detail: the first pass only adds the finalizer and returns (its
Update re-triggers reconciliation); asserting after one pass would test a state
the real system never rests in.

## Exercise

1. Add `TestRetentionAppearsInPruneCommand`: reconcile a CR with
   `retention: 7` and assert the CronJob's container command contains
   `tail -n +8` (retention+1 — off-by-one bugs love this spot; the test
   documents the contract).
2. Optional (regenerate instead of hand-maintaining): run controller-gen and
   confirm the committed deepcopy matches what the generator produces:
   ```powershell
   docker run --rm -v ${PWD}:/w -w /w golang:1.25 sh -c "go run sigs.k8s.io/controller-tools/cmd/controller-gen@v0.16.5 object paths=./api/..."
   git diff --stat api/
   ```

## Checkpoint

- ✅ `go test ./...` — 4/4 green (5/5 after the exercise).
- ✅ For each test you can name the live lab moment it pins down.
- ✅ You can explain what the fake client does NOT simulate, and where that
  missing coverage lives instead (envtest/e2e — and labs 02–05 here).

## Common failures

- `WithStatusSubresource` missing → `r.Status().Update` in the reconciler
  errors with "not found" on the fake client; that line *is* the lesson about
  subresources.
- Your new retention test fails with `tail -n +7` → the off-by-one: keep N
  means delete from line N+1.
- Docker test run can't download modules → corporate proxy; set `GOPROXY` or
  run with local Go.

🎉 Project complete. You built, shipped, secured and tested a real Kubernetes
operator. Rehearse the story: the operator section in
[docs/INTERVIEW_PREP.md](../../../docs/INTERVIEW_PREP.md) §2 turns these six
labs into interview answers — and the honest scope limits (no webhooks, no HA
by default, PVC-not-S3) are listed in the [project README](../../README.md) so
you can name them before the interviewer does.

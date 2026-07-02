# Lab 37 — Bash & Python automation

**Maps to:** extra · **Milestone:** 4 — Operate & Automate · **do anytime after lab 07**

## Concept

The most common DevOps screening exercise is not Kubernetes trivia — it's *"write a script
that…"* (rotates backups, waits for a service, parses a log, reports cloud waste). This lab
adds the glue-scripting layer the project was missing: **Bash** for orchestrating tools, and
**Python** when you need real data structures, argument parsing, or an SDK (boto3).

The professional bar, in both languages, is the same three things: **fail loudly**
(`set -euo pipefail` / `check=True`), **clean up on every exit path** (`trap` /
`try/finally`), and **meaningful exit codes** (so pipelines can gate on you).

## What you'll do

Read, run, and then extend four scripts in [scripts/](../../scripts/):

| Script | Language | Teaches |
|--------|----------|---------|
| `backup_rotate.sh` | Bash | strict mode, arrays/`mapfile`, retention with `xargs -r`, integrity gates |
| `wait_for_healthy.sh` | Bash | polling loops, `trap … EXIT`, timeouts, curl as a probe |
| `verify_backup.py` | Python | subprocess, `try/finally` cleanup, argparse, exit codes |
| `aws_untagged_report.py` | Python | boto3 paginators, set logic, CI-gateable reports |

Plus a set of log-parsing one-liners (`jq`/`awk`) — the "grep the incident" skill.

Bash scripts run from WSL/Git Bash; Python needs 3.10+ (and `pip install boto3` for the AWS one).

## Steps

### 1. Backup rotation (Bash)

With the Compose stack up (lab 04):

```bash
./scripts/backup_rotate.sh 3        # backup, verify header, keep newest 3
./scripts/backup_rotate.sh 3        # run it a few times, watch pruning kick in
ls -lt backups/
```

Read the script before running it — every line is an interview idiom: why `set -euo
pipefail`, why `mapfile` instead of `for f in $(ls …)`, why `xargs -r`, why the `grep` gate
before pruning ("a truncated backup is worse than none — it makes you feel safe").

### 2. Deep-verify the backup (Python)

Rotation checked the file *looks* like a dump. Now prove it *restores* — into a throwaway
container, never your real DB:

```bash
python scripts/verify_backup.py backups/dojo_<newest>.sql --min-steps 24
echo $?     # 0 — this is what a pipeline would gate on
```

Break it on purpose: truncate a copy (`head -c 10000 backups/dojo_x.sql > /tmp/bad.sql`) and
verify that the script fails with exit 1 and a readable error. A verifier you've never seen
fail is as untrustworthy as a backup you've never restored.

### 3. Wait-for-healthy (Bash)

The glue between "deployed" and "smoke-tested" in CI:

```bash
docker compose -f deploy/compose/compose.yaml -f deploy/compose/compose.dev.yaml up -d
./scripts/wait_for_healthy.sh http://localhost:8080/readyz 90 && echo "run smoke tests now"
```

Restart the stack and run it immediately — watch the dots while Postgres comes up, then the
flip to healthy. Note the `trap report EXIT`: the elapsed time prints on *every* exit path,
including Ctrl-C.

### 4. Log-parsing drills (jq/awk)

The API logs structured JSON (one object per line: `msg="http_request"`, `method`, `path`,
`status`, `duration_ms`). Generate some traffic (click around the dashboard, or lab 20's k6),
then, in WSL/Git Bash:

```bash
LOGS() { docker compose -f deploy/compose/compose.yaml logs --no-log-prefix api; }

# status code distribution — the first question in any incident
LOGS | jq -r 'select(.msg=="http_request") | .status' | sort | uniq -c | sort -rn

# top 10 slowest requests
LOGS | jq -r 'select(.msg=="http_request") | "\(.duration_ms)ms\t\(.method) \(.path)"' | sort -rn | head

# which paths are erroring?
LOGS | jq -r 'select(.status >= 500) | .path' | sort | uniq -c | sort -rn

# request count + average latency, in awk
LOGS | jq -r 'select(.msg=="http_request") | .duration_ms' \
     | awk '{ s += $1; n++ } END { printf "requests=%d avg=%.1fms\n", n, s/n }'
```

If non-JSON lines (startup messages) make `jq` choke, armor it:
`jq -R 'fromjson? // empty | select(.msg=="http_request")'`.

### 5. Cloud hygiene report (Python + boto3)

If you've done lab 16 (Terraform provisions tagged EC2), with AWS credentials configured:

```bash
pip install boto3
python scripts/aws_untagged_report.py --required Name project
```

Launch something untagged (or temporarily drop a tag in Terraform) and re-run: exit code 1
and a table naming the offender. That exit code is the point — the same script is a report
for a human *and* a gate for CI.

## How it works

- **Bash strict mode:** `set -e` (stop on error) `-u` (undefined var = bug) `-o pipefail`
  (a failure mid-pipe fails the pipe). Without these, scripts keep marching after failures —
  the classic way backups silently stop happening for six months.
- **`trap` / `try…finally`:** the same idea in both languages — cleanup and reporting must be
  on the exit path, not after the happy path. `verify_backup.py` removes its scratch
  container even when the restore explodes.
- **Exit codes are the API of scripting:** 0 = fine, non-zero = act. Everything else
  (`wait_for_healthy` in a pipeline, the tag report in CI, k6 thresholds in lab 20) builds
  on that contract.
- **Paginators (boto3):** `describe_instances` returns one page; real accounts have more.
  Iterating `get_paginator(...).paginate()` is the difference between a demo script and one
  that's correct in production.
- **shellcheck** is the linter that catches quoting/word-splitting bugs before 3am does:
  `shellcheck scripts/*.sh scripts/chaos/*.sh` (wired into pre-commit — see
  `.pre-commit-config.yaml`).

## Exercise

1. Write `compose_health.sh`: iterate `docker compose ps --format json` with `jq`, exit 1 if
   any service isn't `running`/`healthy`, printing the sick ones. Then run shellcheck on it
   until it's clean.
2. Extend `backup_rotate.sh` to also copy the newest dump to an S3 bucket (`aws s3 cp`) —
   you'll build that bucket properly in lab 40.
3. Python: add `--json` output to `aws_untagged_report.py` (a `--json` flag emitting
   machine-readable output is table stakes for ops tooling).

## Checkpoint

- ✅ `backup_rotate.sh 3` leaves exactly 3 dumps no matter how often you run it.
- ✅ `verify_backup.py` exits 0 on a good dump, 1 on a truncated one — and you watched both.
- ✅ You can answer, from the logs alone with one pipe: "what's the error rate and which
  endpoint is slowest?"
- ✅ `shellcheck` passes on every script in `scripts/`.

## Common failures

- `mapfile: command not found` → you're in macOS's ancient bash 3 or plain `sh`; run with
  bash ≥ 4 (WSL/Git Bash are fine).
- `backup_rotate.sh` finds no dumps → the Compose stack isn't up, so `db-backup` had nothing
  to connect to; check `docker compose ps`.
- `verify_backup.py` times out waiting for ready → the scratch container is slow to init on
  first `postgres:16-alpine` pull; re-run once the image is cached.
- Windows line endings (`\r`) breaking bash → `git config core.autocrlf input`, or add
  `*.sh text eol=lf` to `.gitattributes`.
- `jq: parse error` → prefix lines aren't JSON; use `--no-log-prefix` and the `fromjson?`
  armor above.

➡️ Next: [Lab 38 — Git workflows](../38-git-workflows/)

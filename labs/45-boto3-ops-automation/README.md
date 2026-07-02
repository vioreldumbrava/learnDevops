# Lab 45 — Python + Boto3 ops automation: snapshots & a self-healing monitor

**Maps to:** deepens labs 37/40 · **Milestone:** 5 — Ecosystem breadth · *TWN Bootcamp Module 14* · 💸 runs a `t3.small` briefly

## Concept

Lab 37 scripted against *your own* systems (backups, health waits, chaos). This lab scripts
against the **cloud API** — the daily bread of platform teams. Two archetypes cover most of
what ops Python does:

1. **Resource lifecycle** — enumerate cloud resources by tag, act on them, enforce retention.
   Console clicking doesn't scale and isn't reviewable; a script is both. Also the moment you
   *feel* why tags matter (the script finds volumes the same way lab 44's inventory found
   instances).
2. **Watch-and-heal** — poll something, alert a human, optionally fix it before the human
   arrives. Building the tiny version teaches you exactly what Prometheus + Alertmanager
   (labs 10/12) solve at scale — and when the tiny version is actually the right tool.

**Boto3** is AWS's Python SDK: `boto3.client("ec2")` gives you every EC2 API call as a method.
Same credentials chain as the CLI and Terraform.

## What you'll do

Snapshot the lab-16 server's EBS volume, prune snapshots to a retention count, restore one
into a fresh volume — then point a monitor at the running app, kill the app, and watch the
monitor email you and bring it back up.

## Steps

### 0. Prereqs

The lab-16/44 instance up and serving the app, plus:

```bash
pip install boto3 paramiko        # paramiko only needed for --restart
```

### 1. Backup — snapshot by tag

```bash
python scripts/ec2_snapshots.py backup
python scripts/ec2_snapshots.py list
```

`backup` snapshots **every volume tagged `Project=devops-dojo`** — it discovered the volume
via the tag Terraform wrote, no IDs pasted. Run `backup` two or three more times (snapshots
are incremental; repeats are cheap).

### 2. Cleanup — retention as code

```bash
python scripts/ec2_snapshots.py cleanup --retain 2
python scripts/ec2_snapshots.py list      # only the 2 newest remain
```

Note what protects you here: cleanup only ever deletes snapshots carrying the script's own
`CreatedBy` tag. Scoping destructive automation to *things the automation created* is the
habit that prevents the classic "cleanup script ate the AMI snapshots" incident.

### 3. Restore — prove the backup is real

```bash
python scripts/ec2_snapshots.py restore --snapshot-id snap-0... --attach-to i-0...
# then on the box (ssh -i dojo-key.pem ubuntu@<ip>):
lsblk                                    # the new device appears (e.g. nvme1n1)
sudo mount /dev/nvme1n1p1 /mnt && ls /mnt
```

Same lesson as lab 07, cloud edition: **an unrestored backup is a rumor.** Detach and delete
the scratch volume when done (💸): `aws ec2 detach-volume --volume-id vol-...` then
`aws ec2 delete-volume --volume-id vol-...`.

### 4. Watch-and-heal

Terminal 1 — the monitor (email is optional; without `SMTP_HOST` alerts print to stdout):

```bash
python scripts/website_monitor.py --url http://<public-ip>/ --interval 15 \
  --restart --host <public-ip> --key dojo-key.pem
```

Terminal 2 — cause the outage:

```bash
ssh -i dojo-key.pem ubuntu@<public-ip> "cd /opt/dojo && docker compose --env-file .env \
  -f deploy/compose/compose.yaml -f deploy/compose/compose.prod.yaml stop caddy"
```

Watch terminal 1: `DOWN` → alert → `[restart]` → `UP` → recovery notice. One alert per
outage, not one per failed check — that's the `was_up` state flag, the poor man's version of
Alertmanager's deduplication.

For real email: `export SMTP_HOST=smtp.gmail.com SMTP_USER=you@gmail.com SMTP_PASSWORD=<app
password> ALERT_TO=you@gmail.com` first (Gmail needs an app password, not your login).

## How it works

- [scripts/ec2_snapshots.py](../../scripts/ec2_snapshots.py) — one `boto3.client("ec2")`,
  four subcommands. Everything flows through **paginators** (a bare `describe_*` silently
  truncates at 1000 — same lesson as lab 37's `aws_untagged_report.py`), and restore uses a
  **waiter** (`volume_available`) instead of a sleep loop. The `--attach-to` path reads the
  instance's AZ first: volumes only attach within their AZ — a classic gotcha.
- [scripts/website_monitor.py](../../scripts/website_monitor.py) — stdlib HTTP check +
  `smtplib` email + paramiko SSH heal. The heal command is `compose up -d`, not `restart`:
  `up -d` recreates *missing* containers too. `--once` mode exits 0/1 so cron or systemd
  timers can drive it.
- **When is the tiny monitor right?** A single box, no cluster, checking from *outside* the
  infrastructure (your monitoring shouldn't die with the host it watches). When you have
  Prometheus (labs 10/12/34), it wins on history, routing, silences, and deduplication — the
  interview answer is knowing where the line is.

## Exercise

1. Schedule the backup: a cron line (WSL) or systemd timer that runs
   `ec2_snapshots.py backup` daily and `cleanup --retain 7` weekly. You've rebuilt DLM
   (Data Lifecycle Manager) — now find it in the AWS console and say when you'd use the
   managed one instead.
2. Extend the monitor to check **content**, not just status: fail if the response body
   doesn't contain a marker string (a 200 from a broken app is the sneakiest outage).

## Checkpoint

- ✅ `backup` creates tagged snapshots found by `list`; `cleanup --retain N` prunes to N.
- ✅ A restored volume mounts on the instance and shows real data.
- ✅ The monitor emails (or prints) exactly one alert per outage and heals the app via SSH.
- ✅ You can explain the CreatedBy-tag guard and the AZ constraint on volumes.

## Common failures

- `Unable to locate credentials` → same fix as labs 16/40: `aws configure` or env vars;
  check with `aws sts get-caller-identity`.
- `backup` finds nothing → instance down, or its volume lost the `Project` tag (root volumes
  get tags only if Terraform set them — check `aws ec2 describe-volumes`).
- Restore attach fails with `InvalidParameterValue: ... availability zone` → volume created
  in a different AZ than the instance; pass `--attach-to` and let the script pick the AZ.
- Monitor emails rejected → `SMTP_PORT` wrong (587 = STARTTLS), or Gmail without an app
  password; unset `SMTP_HOST` to fall back to stdout while testing.
- `paramiko` auth error on heal → key path wrong (`--key` is relative to where you run it)
  or the security group no longer allows your IP on 22.

➡️ Back to the map: [docs/CURRICULUM.md](../../docs/CURRICULUM.md)

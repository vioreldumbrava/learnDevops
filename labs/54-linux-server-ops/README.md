# Lab 54 — Linux server operations

**Maps to:** extra · **Milestone:** 4 — Operate & Automate · **Generalist DevOps**

**Run from:** the **repo root** (`learnDevops/`) for the local option, or `/opt/dojo` **on the server** for the EC2 option. Each step says which.

## Concept

Every lab so far has treated the machine as a place where containers happen. Real DevOps jobs
treat it as something you own: it boots, it runs services, it fills up, it gets logged into, and
when it misbehaves at 02:00 nobody hands you `kubectl`.

This is also the round that filters candidates *before* anyone asks about Kubernetes. A
generalist DevOps interview will spend twenty minutes on Linux — units, logs, permissions,
"the disk is full", "the port is in use" — and the answers have to be reflexes, not lookups.

Four things separate someone who has operated a Linux box from someone who has only used one:

1. **The service comes back after a reboot** because *systemd* was told to bring it back — not
   because Docker's `restart: unless-stopped` happened to survive.
2. **Logs are queryable** (`journalctl -u X --since`) instead of `tail`-ed from a file that
   nobody rotates.
3. **Access is deliberate**: named users, sudo scoped in a drop-in, SSH keys only.
4. **A full disk is a five-minute diagnosis**, including the case where `df` and `du` disagree.

[LINUX_FOR_CONTAINERS.md](../../docs/LINUX_FOR_CONTAINERS.md) is the reference for the commands.
This lab is the drill.

## What you'll do

Take ownership of a box: write a systemd unit for the Dojo stack, replace a cron job with a
timer, harden SSH, then break the disk in the nastiest way and find it.

**Where to run it — pick one:**

| Option | Cost | Get it |
|--------|------|--------|
| **EC2** (recommended — it's a real machine) | 💸 a few cents/hour | Labs [16](../16-terraform/) + [17](../17-ansible/), then `ssh ubuntu@<ip>` |
| **Local systemd container** | free | Step 0 below |

```powershell
# Option B — a throwaway box with real systemd, no cloud bill.
docker run -d --name dojo-box --privileged --cgroupns=host `
  -v /sys/fs/cgroup:/sys/fs/cgroup:rw jrei/systemd-ubuntu:22.04
docker exec -it dojo-box bash
# inside: apt update && apt install -y systemd-cron logrotate lsof curl util-linux
```

> The container gets you `systemctl`, `journalctl`, timers and logrotate — everything except
> a genuine `reboot`. For the reboot checkpoint use `docker restart dojo-box`, or do this lab
> on EC2 where the real thing is one command.

---

## Steps

### 1. A unit for the stack (Run from: the server)

Read [`deploy/systemd/dojo.service`](../../deploy/systemd/dojo.service) *before* installing it —
every line is a decision:

```bash
sudo cp deploy/systemd/dojo.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now dojo.service

systemctl status dojo            # active (exited) — correct for Type=oneshot
systemd-analyze verify /etc/systemd/system/dojo.service   # syntax + dependency check
```

Three questions to answer out loud before moving on:

- Why `Type=oneshot` + `RemainAfterExit=yes` and not `Type=simple`?
- Why `Requires=docker.service` **and** `After=docker.service` — what does each one do alone?
- Why `TimeoutStartSec=300`?

### 2. Read its logs the systemd way (Run from: the server)

```bash
journalctl -u dojo -n 50 --no-pager      # last 50 lines from this unit only
journalctl -u dojo -f                    # follow
journalctl -u dojo --since "10 min ago"  # the flag you'll use most in an incident
journalctl -u dojo -p err                # errors and worse
journalctl -u dojo -b -1                 # the PREVIOUS boot — the one that crashed
journalctl --disk-usage                  # and how much space the journal is eating
```

`-b -1` is the one people don't know. "It died overnight and the box rebooted" is unanswerable
without it.

### 3. Timer instead of cron (Run from: the server)

```bash
sudo cp deploy/systemd/dojo-backup.service deploy/systemd/dojo-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now dojo-backup.timer

systemctl list-timers dojo-backup        # NEXT / LEFT / LAST — cron cannot show you this
sudo systemctl start dojo-backup.service # run it NOW, without touching the schedule
journalctl -u dojo-backup -n 20          # the output went to the journal, not a stray logfile
```

Name the three things the timer gives you that `crontab` doesn't: `Persistent=true` (catch-up
after downtime), `RandomizedDelaySec` (no thundering herd), and output that lands in the journal
with the unit's own retention instead of a `>> /var/log/backup.log` that grows forever.

### 4. Access control (Run from: the server)

```bash
sudo adduser --disabled-password --gecos "" deploy
sudo usermod -aG docker deploy

# sudo rights in a DROP-IN, never by editing /etc/sudoers directly
printf 'deploy ALL=(ALL) NOPASSWD: /bin/systemctl restart dojo, /bin/systemctl status dojo\n' \
  | sudo tee /etc/sudoers.d/deploy
sudo visudo -c -f /etc/sudoers.d/deploy    # validate BEFORE you log out. Always.

sudo install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
sudo cp ~/.ssh/authorized_keys /home/deploy/.ssh/
sudo chown deploy:deploy /home/deploy/.ssh/authorized_keys
sudo chmod 600 /home/deploy/.ssh/authorized_keys
```

Then harden `sshd` — in a drop-in again, so a distro upgrade doesn't silently revert you:

```bash
printf 'PermitRootLogin no\nPasswordAuthentication no\nKbdInteractiveAuthentication no\n' \
  | sudo tee /etc/ssh/sshd_config.d/99-hardening.conf
sudo sshd -t                       # syntax check — a typo here locks you out permanently
sudo sshd -T | grep -Ei 'permitrootlogin|passwordauthentication'   # EFFECTIVE config
sudo systemctl reload ssh
```

`sshd -T` prints what the daemon will actually do after all includes and defaults resolve.
`grep` of the config file does not — that's the difference between checking and hoping.

**Keep your current session open** until a *second* terminal proves the new login works. That
habit is worth more in an interview than any flag above.

Firewall, if you're on the EC2 box (the Terraform security group already does this in the
cloud — `ufw` is the on-host layer):

```bash
sudo ufw default deny incoming && sudo ufw default allow outgoing
sudo ufw allow OpenSSH && sudo ufw allow 80,443/tcp
sudo ufw --force enable && sudo ufw status verbose
```

### 5. The disk-full drill (Run from: the server)

This is the part to time yourself on.

```bash
sudo TARGET_DIR=/var/tmp SIZE_MB=2048 ./scripts/chaos/fill-disk.sh
```

Now find it. Work the layers, don't guess:

```bash
df -h                                          # which mount, and how bad
du -xh --max-depth=1 /var 2>/dev/null | sort -h | tail   # -x = don't cross filesystems
```

`du` will not add up to what `df` reports. That gap is the whole point:

```bash
sudo lsof +L1                     # open files with link count 0 = deleted but still held
sudo lsof +L1 | awk '$7 > 100000000'          # only the big ones
ls -l /proc/<PID>/fd | grep deleted            # the same truth, without lsof installed
```

**Fix:** kill the holder (the script printed the PID), or restart the service holding it.
`rm` does nothing here — the name is already gone. Then prevent it:

```bash
sudo cp deploy/systemd/logrotate-dojo /etc/logrotate.d/dojo
sudo logrotate -d /etc/logrotate.d/dojo        # -d = dry run, ALWAYS first
sudo logrotate -f /etc/logrotate.d/dojo        # force one rotation now
```

Read the `copytruncate` comment in that file — it exists because of exactly the failure you
just diagnosed.

### 6. Triage reps (Run from: the server)

Five minutes, no notes. For each symptom, the first two commands and what they distinguish:

| Symptom | You run | You're distinguishing |
|---------|---------|----------------------|
| "Server is slow" | `uptime`, `top` | load average vs CPU% · I/O wait vs compute |
| Out of memory? | `free -m`, `dmesg -T \| grep -i oom` | page cache (fine) vs real exhaustion · did the OOM killer strike |
| Disk full | `df -h`, `du -xh --max-depth=1` | which mount · which directory · (and `lsof +L1` when they disagree) |
| Port in use | `ss -tlnp` | nothing listening vs listening on the wrong interface |
| Runaway process | `ps aux --sort=-%cpu \| head`, `ps aux --sort=-%rss \| head` | CPU hog vs memory hog · whose is it |
| Service died | `systemctl status X`, `journalctl -u X -b -1` | crashed vs never started vs restart-looping |
| Can't reach a host | `ss -tnp`, `curl -v --max-time 5` | DNS vs routing vs firewall vs app |

### 7. Prove the reboot (Run from: the server)

```bash
sudo reboot        # or: docker restart dojo-box
# wait, reconnect, and touch NOTHING:
systemctl is-active dojo
curl -sf http://localhost/api/steps | head -c 80
systemctl list-timers dojo-backup
```

## How it works

- **`Type=oneshot` + `RemainAfterExit=yes`** tells systemd "this command starts something and
  exits; treat the unit as active afterwards". With `Type=simple`, systemd would watch the
  `docker compose up -d` process, see it exit immediately, and call the unit dead.
- **`Requires=` vs `After=`** are orthogonal: `Requires` is a dependency (if docker fails to
  start, dojo doesn't start), `After` is ordering (don't start until docker has). You need both;
  `Requires` alone permits them to start in parallel.
- **A `.timer` + `.service` pair** separates schedule from work, which is why you can trigger a
  run manually without editing the schedule, and why `systemctl list-timers` can show you what
  will happen next.
- **Deleted-but-open files** keep their disk blocks until the last file descriptor closes.
  `df` reads the filesystem's allocation, `du` walks the directory tree — so a file with no
  name is invisible to one and not the other.

## Exercise

Make [lab 17's Ansible playbook](../17-ansible/) install all of this, idempotently: the three
unit files, the logrotate config, the `deploy` user, and the sshd drop-in — with a `handler`
that runs `daemon-reload` only when a unit file actually changed.

Pass: `ansible-playbook playbook.yml` reports `changed=0` on the second run, and a fresh box
provisioned from scratch survives a reboot with the stack up.

## Checkpoint

- ✅ `sudo reboot`, and the Dojo answers on `/api/steps` with **no manual step**.
- ✅ `systemd-analyze verify` is clean; `systemctl list-timers` shows the next backup.
- ✅ `sshd -T` reports `permitrootlogin no` and `passwordauthentication no`, and you can still
  log in as `deploy`.
- ✅ You root-caused the deleted-but-open file **in under five minutes**, and can say in one
  sentence why `du` couldn't see it.

## Common failures

- `systemctl enable` says *"unit file does not exist"* → you copied it but skipped
  `daemon-reload`.
- The unit starts then immediately shows `inactive (dead)` → `Type=simple` instead of
  `oneshot`/`RemainAfterExit`.
- Unit times out on first boot → image pulls exceeded `TimeoutStartSec`; that's why it's 300.
- Locked out of SSH → you edited the config without `sshd -t` and without a second session
  open. On EC2, recover with the serial console or by detaching the volume; on the container,
  `docker exec`.
- `logrotate` "did nothing" → without `-f` it respects the schedule; and check
  `/var/lib/logrotate/status` for when it last ran.
- `lsof` not installed → `ls -l /proc/*/fd 2>/dev/null | grep deleted` gets you there.

## Maps to

Interview §8's Linux triage table (turns those one-liners into reflexes), lab
[17](../17-ansible/) (which should *deploy* this), lab [35](../35-incident-response/) (the
container-level versions of the same drills), and lab [37](../37-scripting-automation/) (whose
`backup_rotate.sh` the timer runs).

➡️ Next: [Lab 55 — Postgres under load](../55-postgres-operations/)

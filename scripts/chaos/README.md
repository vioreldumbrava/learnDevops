# Chaos injectors (lab 35)

One-command fault injection for the break-fix drills in
[labs/35-incident-response](../../labs/35-incident-response/). Bash — run from WSL or Git
Bash, from anywhere (each script finds the repo root itself).

| Script | Injects | Drill |
|--------|---------|-------|
| `crashloop.sh` | CrashLoopBackOff (broken command) | 1 |
| `oom.sh` | OOMKilled (8Mi memory limit) | 2 |
| `kill-db.sh` | Postgres gone → readiness cascade | 3 |
| `break-selector.sh` | Service selector typo (silent 502) | 4 |
| `bad-image.sh` | ImagePullBackOff (nonexistent tag) | 5 |
| `readonly-db.sh` | DB rejects writes (disk-full signature) | 7 |
| `roulette.sh` | one of the above, at random, without telling you | 8 |
| `heal.sh` | reverts **everything** back to healthy | — |

`roulette.sh` writes what it did to `scripts/chaos/.last_fault` — only peek after you've
diagnosed. `heal.sh` is safe to run at any point, including between drills.

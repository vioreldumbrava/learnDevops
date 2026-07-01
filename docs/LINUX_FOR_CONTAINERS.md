# Linux Basics For Working With Containers

The Linux commands you need before Docker, Kubernetes, and a VPS feel comfortable.
Written for **this repo** (DevOps Dojo + the `ai-assistant/` project) and an Ubuntu
EC2/VPS server. You don't need to memorize everything — learn the flow:

1. Where am I?
2. What files are here?
3. What is running?
4. What do the logs say?
5. Is the port open / firewall right?
6. Is disk or memory full?
7. How do I safely edit, restart, or roll back?

Project conventions used below:

- On a server the project usually lives at **`/opt/dojo`** (see the Ansible playbook).
- Compose files live under **`deploy/compose/`**; the prod stack is
  `-f deploy/compose/compose.yaml -f deploy/compose/compose.prod.yaml`.
- App services: `db`, `redis`, `migrate`, `api`, `worker`, `frontend`, `caddy`
  (observability overlay adds `prometheus`, `grafana`, `loki`, `promtail`, `tempo`,
  `alertmanager`, `blackbox-exporter`).

## 1. Know Where You Are

```bash
pwd                 # print current folder, e.g. /opt/dojo
ls                  # list files
ls -la              # long list incl. hidden files like .env (-l details, -a all)
cd /opt/dojo        # change folder
cd ..               # up one
cd ~                # home
cd -                # back to the previous folder
```

## 2. Read Files Safely

```bash
cat .env                                   # print a small file
less docs/DOCKER_LEARNING_PATH.md          # page a big file (Space/b, /search, q to quit)
head -40 deploy/compose/compose.yaml       # first lines
tail -40 deploy/compose/compose.yaml       # last lines
tail -f /var/log/syslog                    # follow a growing file (Ctrl+C to stop)
grep -R "grafana" deploy/                   # search recursively
rg "grafana" deploy/                        # ripgrep (nicer, if installed)
```

## 3. Edit Files

```bash
nano .env           # Ctrl+O save, Enter confirm, Ctrl+X exit
```

`vim` is everywhere if `nano` isn't: `vim file` → `i` to insert, `Esc` then `:wq` to
save+quit (`:q!` to quit without saving). Be careful with `.env`: it holds passwords.

## 4. Understand Paths

```bash
/opt/dojo/deploy/compose/compose.yaml   # absolute path (starts at /)
deploy/compose/compose.yaml             # relative path (from where you are)
.    # current folder     ..   # parent     ~    # your home
```

## 5. Create, Copy, Move, Remove, Archive

```bash
mkdir -p /opt/dojo/backups              # make folder(s)
cp .env.example .env                    # copy a file
cp -r deploy deploy.bak                 # copy a folder
mv old.txt new.txt                      # move / rename
rm old.txt                              # remove a file
rm -rf old-folder                       # remove a folder + contents (dangerous!)

tar -czf backup.tgz backups/            # create a gzip archive
tar -xzf backup.tgz                     # extract it
```

Before any `rm -rf`, check where you are: `pwd && ls -la`.

## 6. Permissions And Ownership (chmod / chown)

### Read the permissions first

```bash
ls -l .env
# -rw-r--r-- 1 ubuntu ubuntu 1234 ... .env
```

That first block is `type` + three permission groups of `rwx`:

```text
 -   rw-      r--      r--
type owner    group    others
     (u)      (g)      (o)
```

`r`=read, `w`=write, `x`=execute (for a file) or enter/list (for a directory), `-`=off.
So `-rw-r--r--` = owner can read/write; group and others can only read.

### Change permissions — two ways with `chmod`

**Symbolic** (easiest to reason about): `who`(`u`,`g`,`o`,`a`) + `op`(`+` add, `-` remove,
`=` set exactly) + `perms`(`r`,`w`,`x`):

```bash
chmod +x script.sh        # make executable (everyone)
chmod u+x script.sh       # executable for the owner only
chmod g-w file            # remove write from the group
chmod o-rwx secret        # remove ALL access for "others"
chmod a+r file            # readable by all (a = u+g+o)
chmod u=rw,go= .env       # owner read/write; group & others nothing  (same as 600)
```

**Numeric** (compact): add `r=4`, `w=2`, `x=1` per group, in order owner-group-others:

| Digit | Perms | Meaning |
|-------|-------|---------|
| 7 | rwx | read + write + execute |
| 6 | rw- | read + write |
| 5 | r-x | read + execute |
| 4 | r-- | read only |
| 0 | --- | none |

```bash
chmod 400 devDockerKey.pem   # owner read-only        (required for SSH keys)
chmod 600 .env               # owner read/write only  (secrets)
chmod 644 file               # owner rw, others read
chmod 755 script.sh          # owner rwx, others r-x   (scripts, directories)
chmod 700 ~/.ssh             # owner-only directory
```

### Whole directories (recursive)

```bash
chmod -R 755 somedir                 # apply to everything under somedir
chmod -R u+rwX /opt/dojo/backups     # capital X = set execute on DIRECTORIES only
                                     #   (and already-executable files), not plain files
```

Use capital `X` for mixed trees so you don't accidentally mark every data file executable.

### Change ownership with `chown` / `chgrp`

```bash
sudo chown ubuntu file                  # change owner
sudo chown ubuntu:ubuntu file           # change owner AND group (user:group)
sudo chown -R ubuntu:ubuntu /opt/dojo   # recursively fix a project folder
sudo chgrp docker /var/run/docker.sock  # change only the group
```

Use `sudo` only when needed; if *everything* needs it, ownership is probably wrong (fix it
once with `chown -R`). Common fixes in this project: `chmod 400` your `.pem` key,
`chmod 600 .env`, `chmod +x` a helper script, and `chown -R ubuntu:ubuntu /opt/dojo` after
copying files as root.

## 7. Packages On Ubuntu

```bash
sudo apt update                                   # refresh package lists
sudo apt install -y git curl jq docker.io docker-compose-v2
sudo apt upgrade -y
```

Package manager by system: Ubuntu/Debian → `apt`; Amazon Linux/Fedora → `dnf`;
Alpine containers → `apk`.

## 8. Services With systemctl (and their logs)

```bash
sudo systemctl status docker      # is it running?
sudo systemctl start docker
sudo systemctl restart docker
sudo systemctl enable --now docker # start now + on every boot

# systemd logs (the other half of the picture):
journalctl -u docker --no-pager | tail -50   # docker service logs
journalctl -u docker -f                        # follow live
journalctl -p err -b                           # errors since last boot
```

## 9. Users And Groups

```bash
whoami
groups
sudo usermod -aG docker ubuntu    # run docker without sudo
exit                              # then reconnect (group applies on next login)
```

## 10. Processes, Signals & Background Jobs

```bash
ps aux                     # all processes
ps aux | grep docker       # find one
top                        # live view (q to quit); htop is nicer (sudo apt install -y htop)

# Signals & control:
# Ctrl+C  stop the foreground command      Ctrl+Z  suspend it
long-running-command &     # run in the background
jobs; fg; bg               # list / foreground / background jobs
nohup ./run.sh &           # keep running after you log out
kill <pid>                 # ask a process to stop (SIGTERM)
kill -9 <pid>              # force kill (last resort)
pkill -f pattern           # kill by command pattern

watch -n 2 'docker compose ps'   # re-run a command every 2s
```

## 11. Disk And Memory

```bash
df -h                              # disk space
du -sh /opt/dojo                   # size of a folder
du -h --max-depth=1 /opt/dojo | sort -h   # biggest subfolders
free -h                            # memory
docker system df                   # Docker's disk usage (images fill small disks fast)
docker system prune                # remove stopped containers, unused nets, build cache
docker system prune -a             # also unused images (re-downloaded next build)
```

## 12. Networking Checks

```bash
ip addr                            # this machine's IPs
sudo ss -tulpn                     # listening ports + owning process
ping -c 3 example.com              # reachability
curl -I http://localhost           # headers only (is it up?)
nslookup example.com               # DNS (sudo apt install -y dnsutils if missing)

# Check THIS project's routes through Caddy on the server:
curl -I http://localhost           # -> frontend
curl    http://localhost/healthz   # -> api liveness
curl -s http://localhost/api/steps # -> api data

# Check a REMOTE model server (the "connect to another PC" feature):
curl http://<gpu-pc-ip>:11434/api/tags   # Ollama: lists models => reachable
curl http://<gpu-pc-ip>:1234/v1/models   # LM Studio
```

## 13. Firewall With ufw

On a public server, expose only what must be public. Caddy is the entrypoint (80/443);
databases and app ports stay private.

```bash
sudo ufw allow OpenSSH        # keep your SSH access! (port 22)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

Do **not** open `5432` (Postgres), `6379` (Redis), `8080`/`8000` (apps), or `11434`
(Ollama) to the world. If a machine serves a model to your app host only, scope it:

```bash
sudo ufw allow from <app-host-ip> to any port 11434 proto tcp
```

## 14. SSH Basics

From PowerShell (Windows) to the server:

```powershell
ssh -i .\devDockerKey.pem ubuntu@<server-ip>
scp -i .\devDockerKey.pem .\local.txt ubuntu@<server-ip>:/home/ubuntu/   # push
scp -i .\devDockerKey.pem ubuntu@<server-ip>:/home/ubuntu/remote.txt .    # pull
```

On a Linux/macOS control node (e.g. for Ansible), the key must be private or SSH refuses it:

```bash
chmod 400 devDockerKey.pem
```

Save typing with `~/.ssh/config`:

```text
Host dojo
    HostName <server-ip>
    User ubuntu
    IdentityFile ~/.ssh/devDockerKey.pem
```

Then just `ssh dojo`. Never commit `.pem` keys to Git (this repo gitignores `*.pem`).

## 15. Working With APIs: curl + jq

`jq` formats and filters JSON — invaluable for the app API and the AI assistant.

```bash
sudo apt install -y jq

# Pretty-print / filter the app API:
curl -s http://localhost/api/steps | jq '.[0]'
curl -s http://localhost/api/steps | jq 'length'

# POST JSON to the AI assistant and extract just the answer:
curl -s http://localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"How do backups work?"}' | jq -r '.answer'

# Stream tokens (server-sent events) — -N disables buffering:
curl -N http://localhost:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"Explain KEDA","stream":true}'
```

## 16. Docker Commands You Will Use Constantly

```bash
docker version
docker compose version
docker ps                 # running containers
docker ps -a              # incl. stopped
docker images
docker system df
docker system prune
```

## 17. Docker Compose Commands For This Project

From the project folder (`cd /opt/dojo`). The prod stack uses two `-f` files:

```bash
DC="docker compose --env-file .env -f deploy/compose/compose.yaml -f deploy/compose/compose.prod.yaml"

$DC config                       # validate + show the merged config
$DC up -d --build                # start the prod stack (caddy + app + db/redis)
$DC ps                           # status
$DC logs -f caddy api frontend   # follow logs
$DC down                         # stop
```

Observability overlay (adds the monitoring stack; ports bind to localhost — tunnel to reach):

```bash
docker compose --env-file .env \
  -f deploy/compose/compose.yaml \
  -f deploy/compose/compose.prod.yaml \
  -f deploy/compose/compose.observability.yaml \
  up -d prometheus grafana loki promtail tempo alertmanager blackbox-exporter
```

## 18. Container Logs

```bash
$DC logs api                 # one service
$DC logs -f caddy            # follow live
$DC logs --tail=100 api      # last 100 lines
```

Useful log targets: `caddy`, `frontend`, `api`, `worker`, `db`, `redis` (and the
observability services when that overlay is up).

## 19. Enter A Running Container

```bash
$DC exec db psql -U dojo -d dojo         # open a psql shell in Postgres
$DC exec frontend sh                     # shell into the frontend (Nginx/alpine)
$DC exec redis redis-cli ping            # talk to Redis
```

Notes:

- Small images ship `sh`, not `bash` — use `sh`.
- The **`api` image is distroless** (no shell) for security, so `exec api sh` fails —
  that's expected. Use its healthcheck binary instead: `$DC exec api /api -healthcheck`,
  or debug from a service that has a shell.

## 20. Environment Variables

```bash
env                       # all variables
echo "$SITE_DOMAIN"       # one variable
export SITE_DOMAIN=:80    # set for this shell only
cat .env                  # Compose reads deploy values from here
```

Use `--env-file .env` when running the prod overlay (see the `$DC` alias above).

## 21. Redirection, Pipes & Text Tools

```bash
docker compose ps > status.txt      # write (overwrite)
date >> deploy-log.txt              # append
docker ps | grep grafana           # pipe into another command
$DC logs caddy | grep -i error     # filter logs

# Handy text tools:
sudo ss -tulpn | awk '{print $5}'  # a column
cat access.log | cut -d' ' -f1 | sort | uniq -c | sort -rn | head   # top IPs
wc -l file                          # count lines
```

## 22. Exit Codes

```bash
curl -I http://localhost
echo $?      # 0 = success, anything else = failure
```

## 23. kubectl Quick Reference

For the Kubernetes track (labs 22, 27–34). `-n` selects the namespace.

```bash
kubectl get pods -n devops-dojo
kubectl get pods,svc,ingress -n devops-dojo
kubectl get pods -A                        # every namespace
kubectl describe pod <pod> -n devops-dojo  # events (why it won't start)
kubectl logs -f deploy/api -n devops-dojo
kubectl exec -it deploy/frontend -n devops-dojo -- sh
kubectl apply -f deploy/k8s/base/
kubectl rollout status deploy/api -n devops-dojo
kubectl top pods -n devops-dojo            # needs metrics-server
kubectl config current-context            # which cluster am I pointed at?
```

## 24. Shell Productivity

```bash
history            # commands you've run
!!                 # repeat the last command (e.g. sudo !!)
!123               # run history item 123
# Ctrl+R           reverse-search your history (type a few chars)
# Tab              autocomplete commands, paths, and (often) docker/kubectl args
# Ctrl+L or clear  clear the screen
alias dc='docker compose --env-file .env -f deploy/compose/compose.yaml -f deploy/compose/compose.prod.yaml'
```

## 25. Common Debugging Flow

When a containerized app misbehaves, go in order:

```bash
cd /opt/dojo
$DC config                      # 1. does the config parse?
$DC ps                          # 2. what's running / restarting?
$DC logs --tail=100 api caddy   # 3. what do the logs say?
sudo ss -tulpn                  # 4. is the port listening?
curl -I http://localhost        # 5. does it respond?
df -h; free -h; docker system df # 6. out of disk/memory?
```

On Kubernetes: `kubectl get pods -n <ns>` → `kubectl describe pod <pod>` →
`kubectl logs <pod>`.

## 26. Commands To Avoid Until You Understand Them

```bash
rm -rf /            rm -rf *
docker volume prune          docker system prune -a --volumes
sudo chmod -R 777 /          sudo chown -R ubuntu:ubuntu /
```

These delete data or break permissions. Use cleanup commands only when you know what
they remove.

## 27. Mini Practice Path

On your server:

```bash
whoami; pwd; ls -la
cd /opt/dojo && ls -la
cat .env
docker ps
docker compose --env-file .env -f deploy/compose/compose.yaml -f deploy/compose/compose.prod.yaml ps
curl -I http://localhost
curl -s http://localhost/api/steps | jq 'length'
sudo ufw status
df -h; free -h
```

If those feel comfortable, you have enough Linux to debug most container problems and to
operate both projects in this repo.

# Linux Basics For Working With Containers

This guide is for the Linux commands you need before Docker starts to feel
comfortable. It is written for this project and for an Ubuntu EC2/VPS server.

You do not need to memorize everything. Learn the flow:

1. Where am I?
2. What files are here?
3. What is running?
4. What do the logs say?
5. Is the port open?
6. Is disk or memory full?
7. How do I safely edit or restart?

## 1. Know Where You Are

Print the current folder:

```bash
pwd
```

Example output:

```text
/opt/dbc/current
```

List files:

```bash
ls
```

List files with details:

```bash
ls -la
```

Why `-la` is useful:

- `-l` shows permissions, owner, size, and date.
- `-a` shows hidden files like `.env`.

Change folder:

```bash
cd /opt/dbc/current
```

Go up one folder:

```bash
cd ..
```

Go to your home folder:

```bash
cd ~
```

## 2. Read Files Safely

Print a small file:

```bash
cat .env
```

Read a larger file page by page:

```bash
less docs/DOCKER_LEARNING_PATH.md
```

Inside `less`:

```text
Space  next page
b      previous page
/text  search
q      quit
```

Print the first lines:

```bash
head -40 docker/compose.yaml
```

Print the last lines:

```bash
tail -40 docker/compose.yaml
```

Follow a changing log file:

```bash
tail -f /var/log/syslog
```

Search inside files:

```bash
grep -R "grafana" docker/
```

If `rg` is installed, it is nicer:

```bash
rg "grafana" docker/
```

## 3. Edit Files

Open a file with Nano:

```bash
nano .env
```

Inside Nano:

```text
Ctrl+O  save
Enter   confirm filename
Ctrl+X  exit
```

Edit a specific config on the EC2 server:

```bash
cd /opt/dbc/current
nano .env
```

Be careful with `.env`: it can contain passwords and deployment settings.

## 4. Understand Paths

Absolute path starts from `/`:

```bash
/opt/dbc/current/docker/compose.yaml
```

Relative path starts from where you are:

```bash
docker/compose.yaml
```

Current folder:

```bash
.
```

Parent folder:

```bash
..
```

Home folder:

```bash
~
```

For this project on EC2, the usual folder is:

```bash
/opt/dbc/current
```

## 5. Create, Copy, Move, Remove

Create a folder:

```bash
mkdir -p /opt/dbc/backups
```

Copy a file:

```bash
cp docker/deploy/env.example .env
```

Copy a folder:

```bash
cp -r output/docker_complete_solution output/docker_complete_solution_copy
```

Move or rename:

```bash
mv old-name.txt new-name.txt
```

Remove a file:

```bash
rm old-file.txt
```

Remove a folder and everything inside it:

```bash
rm -rf old-folder
```

Be very careful with `rm -rf`. Always check where you are first:

```bash
pwd
ls -la
```

## 6. Permissions And Ownership

Show permissions:

```bash
ls -la
```

Example:

```text
-rw-r--r-- 1 ubuntu ubuntu 1234 Jun 29 18:00 .env
drwxr-xr-x 2 ubuntu ubuntu 4096 Jun 29 18:00 docker
```

Meaning:

- `r` means read.
- `w` means write.
- `x` means execute or enter a folder.
- First group is owner permissions.
- Second group is group permissions.
- Third group is everyone else.

Change owner:

```bash
sudo chown -R ubuntu:ubuntu /opt/dbc
```

Make a script executable:

```bash
chmod +x script.sh
```

Run a command as administrator:

```bash
sudo systemctl status docker
```

Use `sudo` only when needed. If every command needs `sudo`, ownership may be
wrong.

## 7. Packages On Ubuntu

Update package lists:

```bash
sudo apt update
```

Install packages:

```bash
sudo apt install -y git curl docker.io docker-compose-v2
```

Upgrade packages:

```bash
sudo apt upgrade -y
```

Important Ubuntu note:

```text
Ubuntu uses apt.
Amazon Linux and Fedora use dnf.
Alpine containers use apk.
Debian and Ubuntu containers use apt.
```

If you see `dnf: command not found` on Ubuntu, use `apt`.

## 8. Services With systemctl

Check Docker service:

```bash
sudo systemctl status docker
```

Start Docker:

```bash
sudo systemctl start docker
```

Restart Docker:

```bash
sudo systemctl restart docker
```

Start Docker automatically after reboot:

```bash
sudo systemctl enable docker
```

## 9. Users And Groups

Show current user:

```bash
whoami
```

Show your groups:

```bash
groups
```

Allow the `ubuntu` user to run Docker without `sudo`:

```bash
sudo usermod -aG docker ubuntu
exit
```

Then reconnect with SSH. Group changes apply on the next login.

## 10. Processes And Resource Usage

Show running processes:

```bash
ps aux
```

Search for a process:

```bash
ps aux | grep docker
```

Live CPU and memory view:

```bash
top
```

If available, `htop` is easier:

```bash
sudo apt install -y htop
htop
```

Quit `top` or `htop`:

```text
q
```

## 11. Disk And Memory

Check disk space:

```bash
df -h
```

Check folder size:

```bash
du -sh /opt/dbc/current
```

Find large folders:

```bash
du -h --max-depth=1 /opt/dbc/current | sort -h
```

Check memory:

```bash
free -h
```

Docker images can fill small EC2 disks quickly. Check Docker disk usage:

```bash
docker system df
```

Clean unused Docker data:

```bash
docker system prune
```

More aggressive cleanup:

```bash
docker system prune -a
```

Be careful: `docker system prune -a` removes unused images, so future builds may
need to download them again.

## 12. Networking Checks

Show IP addresses:

```bash
ip addr
```

Show listening ports:

```bash
sudo ss -tulpn
```

Check if a local service responds:

```bash
curl -I http://localhost
```

Check the EC2 app from the server itself:

```bash
curl -I http://localhost
curl -I http://localhost/artifacts/
curl -I http://localhost/grafana/
```

Check DNS:

```bash
nslookup example.com
```

If `nslookup` is missing:

```bash
sudo apt install -y dnsutils
```

## 13. SSH Basics

Connect from PowerShell to EC2:

```powershell
ssh -i .\devDockerKey.pem ubuntu@51.21.251.231
```

Copy a file from Windows to EC2:

```powershell
scp -i .\devDockerKey.pem .\local-file.txt ubuntu@51.21.251.231:/home/ubuntu/
```

Copy a file from EC2 to Windows:

```powershell
scp -i .\devDockerKey.pem ubuntu@51.21.251.231:/home/ubuntu/remote-file.txt .
```

Exit the server:

```bash
exit
```

Never commit `.pem` keys to Git.

## 14. Docker Commands You Will Use Constantly

Show Docker version:

```bash
docker version
```

Show Compose version:

```bash
docker compose version
```

List running containers:

```bash
docker ps
```

List all containers, including stopped:

```bash
docker ps -a
```

List images:

```bash
docker images
```

Show Docker disk usage:

```bash
docker system df
```

Remove stopped containers, unused networks, and build cache:

```bash
docker system prune
```

## 15. Docker Compose Commands For This Project

Go to the project folder first:

```bash
cd /opt/dbc/current
```

Show the final combined Compose config:

```bash
docker compose --env-file .env -f docker/compose.yaml -f docker/compose.prod.yaml config
```

Start the main production app:

```bash
docker compose --env-file .env \
  -f docker/compose.yaml \
  -f docker/compose.prod.yaml \
  up -d --build frontend artifact-server caddy
```

Start Grafana and monitoring:

```bash
docker compose --env-file .env \
  -f docker/compose.yaml \
  -f docker/compose.prod.yaml \
  -f docker/compose.observability.yaml \
  up -d prometheus blackbox-exporter loki promtail grafana caddy
```

Show service status:

```bash
docker compose --env-file .env \
  -f docker/compose.yaml \
  -f docker/compose.prod.yaml \
  -f docker/compose.observability.yaml \
  ps
```

Follow logs:

```bash
docker compose --env-file .env \
  -f docker/compose.yaml \
  -f docker/compose.prod.yaml \
  logs -f caddy frontend artifact-server
```

Stop the main stack:

```bash
docker compose --env-file .env \
  -f docker/compose.yaml \
  -f docker/compose.prod.yaml \
  down
```

## 16. Container Logs

See logs for one service:

```bash
docker compose --env-file .env \
  -f docker/compose.yaml \
  -f docker/compose.prod.yaml \
  logs caddy
```

Follow logs live:

```bash
docker compose --env-file .env \
  -f docker/compose.yaml \
  -f docker/compose.prod.yaml \
  logs -f caddy
```

Show only the last lines:

```bash
docker compose --env-file .env \
  -f docker/compose.yaml \
  -f docker/compose.prod.yaml \
  logs --tail=100 caddy
```

Useful log targets in this project:

```bash
caddy
frontend
artifact-server
grafana
prometheus
loki
promtail
```

## 17. Enter A Running Container

Open a shell inside a container:

```bash
docker compose --env-file .env \
  -f docker/compose.yaml \
  -f docker/compose.prod.yaml \
  exec frontend sh
```

Inside many small containers, `bash` is not installed. Use `sh`.

Run a one-off command inside a service container:

```bash
docker compose --env-file .env \
  -f docker/compose.yaml \
  -f docker/compose.prod.yaml \
  exec caddy wget -q -O - http://localhost/health
```

Exit a container shell:

```bash
exit
```

## 18. Environment Variables

Print all environment variables:

```bash
env
```

Print one variable:

```bash
echo "$SITE_DOMAIN"
```

Set a variable only for the current shell:

```bash
export SITE_DOMAIN=http://:80
```

Compose usually reads deployment values from `.env`:

```bash
cat .env
```

For this project, use `--env-file .env` when running the production overlay:

```bash
docker compose --env-file .env -f docker/compose.yaml -f docker/compose.prod.yaml config
```

## 19. Redirection And Pipes

Send command output into a file:

```bash
docker compose ps > compose-status.txt
```

Append output to a file:

```bash
date >> deploy-log.txt
```

Pipe output into another command:

```bash
docker ps | grep grafana
```

Search logs:

```bash
docker compose logs caddy | grep error
```

## 20. Exit Codes

Linux commands return an exit code:

- `0` means success.
- Anything else usually means failure.

Show the previous command exit code:

```bash
echo $?
```

Example:

```bash
curl -I http://localhost
echo $?
```

## 21. Common Debugging Flow

When a containerized app does not work, use this order:

1. Go to the project folder:

```bash
cd /opt/dbc/current
```

2. Validate Compose:

```bash
docker compose --env-file .env -f docker/compose.yaml -f docker/compose.prod.yaml config
```

3. Check containers:

```bash
docker compose --env-file .env -f docker/compose.yaml -f docker/compose.prod.yaml ps
```

4. Check logs:

```bash
docker compose --env-file .env -f docker/compose.yaml -f docker/compose.prod.yaml logs --tail=100 caddy
```

5. Check ports:

```bash
sudo ss -tulpn
```

6. Check HTTP from the server:

```bash
curl -I http://localhost
curl -I http://localhost/artifacts/
curl -I http://localhost/grafana/
```

7. Check disk and memory:

```bash
df -h
free -h
docker system df
```

## 22. Commands To Avoid Until You Understand Them

These commands are powerful and can delete important data:

```bash
rm -rf /
rm -rf *
docker volume prune
docker system prune -a --volumes
sudo chmod -R 777 /
sudo chown -R ubuntu:ubuntu /
```

Use cleanup commands only when you understand what they remove.

## 23. Mini Practice Path

Run these on your EC2 instance:

```bash
whoami
pwd
ls -la
cd /opt/dbc/current
ls -la
cat .env
docker ps
docker compose --env-file .env -f docker/compose.yaml -f docker/compose.prod.yaml ps
curl -I http://localhost
df -h
free -h
```

If those commands feel comfortable, you already have enough Linux to debug most
basic container problems.


# Ansible — configure the server & deploy

Takes the bare Ubuntu box from Terraform and makes it run DevOps Dojo: installs Docker,
clones the repo, writes `.env`, and brings up the production stack behind Caddy. This is
**configuration management** — idempotent and repeatable, unlike hand-typed SSH commands.

## Prerequisites

- A control node with Ansible (Linux/macOS, or **WSL** on Windows — Ansible has no native
  Windows control node). Install: `pipx install ansible` or `pip install ansible`.
- The server from [../terraform](../terraform) (or any Ubuntu VPS you can SSH into).
- The SSH key (`devDockerKey.pem`) reachable at the path in `ansible.cfg`.

## Use

```bash
cd deploy/ansible
cp inventory.ini.example inventory.ini
# paste Terraform's `ansible_inventory_line` output into inventory.ini

# Check connectivity
ansible dojo -m ping

# Deploy (override the placeholder vars with real values)
ansible-playbook playbook.yml \
  -e repo_url=https://github.com/<you>/<repo>.git \
  -e postgres_password=$(openssl rand -hex 16) \
  -e site_domain=":80" \
  -e acme_email=you@example.com
```

Then open `http://<server-ip>`.

## What it does (tasks)

1. Install `docker.io`, `docker-compose-v2`, `git`.
2. Enable Docker at boot; add the deploy user to the `docker` group.
3. Create `/opt/dojo` and clone the repo into it.
4. Render `/opt/dojo/.env` from `templates/env.j2`.
5. `docker compose ... -f compose.prod.yaml up -d --build`.

## Re-running

The playbook is idempotent: re-running updates the repo and restarts changed services. To
ship a new version, push to your repo and re-run the playbook (or `git pull` + compose up).

## Notes

- Real secrets: pass with `--extra-vars` or an Ansible Vault file — never commit them.
- This builds images on the server (simple). A production-grade flow pulls pre-built images
  from GHCR (labs 13 & 15) instead — a natural next iteration.

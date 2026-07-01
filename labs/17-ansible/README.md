# Lab 17 — Configuration management: Ansible

**Maps to:** extra (fills a gap in the original path) · **Milestone:** 2

## Concept

Terraform gave you a bare server. **Configuration management** installs and configures the
software on it — **repeatably and idempotently**, so running it twice is safe and the result
is always the same. **Ansible** connects over SSH and applies a list of declarative tasks; no
agent needed on the server.

## What you'll do

Install Docker on the Terraform-provisioned box, deploy the production stack, and reach the
app over the internet — all with one command.

## Steps

Prereqs: an Ansible control node (Linux/macOS/**WSL** — not native Windows) and the server
from lab 16.

```bash
cd deploy/ansible
cp inventory.ini.example inventory.ini
# paste Terraform's `ansible_inventory_line` output into inventory.ini

ansible dojo -m ping        # expect "pong"

ansible-playbook playbook.yml \
  -e repo_url=https://github.com/<you>/<repo>.git \
  -e postgres_password=$(openssl rand -hex 16) \
  -e site_domain=":80" \
  -e acme_email=you@example.com
```

Then open `http://<server-ip>` — the dashboard, live, behind Caddy.

## How it works

[playbook.yml](../../deploy/ansible/playbook.yml) runs, in order: install Docker + Compose +
git, enable Docker, add the user to the `docker` group, create `/opt/dojo`, clone the repo,
render `.env` from [templates/env.j2](../../deploy/ansible/templates/env.j2), and
`docker compose ... -f compose.prod.yaml up -d --build`. Every task is **idempotent** — the
`apt`/`git`/`template` modules only change things when needed, so re-running is safe.

Config lives in [ansible.cfg](../../deploy/ansible/ansible.cfg) (inventory, SSH key, remote
user). Secrets are passed with `--extra-vars`, never committed (use Ansible Vault for real
deployments).

## Exercise

Run the playbook a **second time** with no changes and read the `PLAY RECAP`: `changed=0`
for the idempotent tasks. Then push a change to your repo and re-run — only the git + compose
tasks report `changed`, and the new version is live. That's config management vs. a one-off script.

## Checkpoint

- ✅ `ansible dojo -m ping` returns `pong`.
- ✅ `ansible-playbook` completes with `failed=0`.
- ✅ `http://<server-ip>` serves the app; toggling a lab persists.

## Common failures

- `ansible` not found on Windows → run from WSL/Linux/macOS; there's no native Windows control node.
- SSH/permission errors → check `private_key_file` in `ansible.cfg` and that port 22 allows your IP.
- Compose builds run out of memory on `t3.small` → use `t3.medium`, or deploy pre-built GHCR
  images instead of building on the box.

Milestone 2 complete — you can now build, test, publish, provision, and deploy automatically.
Milestone 3 (HTTPS, hardening, load testing, scaling, Kubernetes) is next; see
[docs/CURRICULUM.md](../../docs/CURRICULUM.md).

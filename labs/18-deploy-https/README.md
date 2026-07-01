# Lab 18 — Deploy to a VPS/EC2 with HTTPS

**Maps to:** original §15–16 · **Milestone:** 3

## Concept

Put the app on a real server reachable from the internet, with **automatic HTTPS**. Caddy
obtains and renews Let's Encrypt certificates for you the moment it sees a real domain and
ports 80/443 — no manual certificate handling.

## What you'll do

Take the server from labs 16–17 (Terraform + Ansible) and give it a domain with valid TLS.

## Steps

Prereqs: the stack already deployed by Ansible (lab 17), and a domain you control.

1. **Point DNS at the server.** Create an `A` record for your domain → the Elastic IP from
   Terraform (`terraform output public_ip`).
2. **Set the domain + email** and redeploy so Caddy switches from HTTP to HTTPS:
   ```bash
   ansible-playbook playbook.yml \
     -e repo_url=https://github.com/<you>/<repo>.git \
     -e postgres_password=<same-as-before> \
     -e site_domain=dojo.example.com \
     -e acme_email=you@example.com
   ```
   (Or manually on the box: edit `/opt/dojo/.env` `SITE_DOMAIN`/`ACME_EMAIL`, then
   `docker compose --env-file .env -f deploy/compose/compose.yaml -f deploy/compose/compose.prod.yaml up -d`.)
3. Open `https://dojo.example.com` — a valid padlock, issued automatically.

## How it works

The [Caddyfile](../../deploy/caddy/Caddyfile) uses `{$SITE_DOMAIN}`. With a bare `:80` it
serves plain HTTP (local testing); with a real hostname Caddy runs the ACME challenge over
port 80, gets a cert, and serves HTTPS on 443 — renewing automatically. Only Caddy is public
(80/443); the app/DB ports stay private (the security group from Terraform enforces this too).

## Update & rollback

```bash
# Update: pull the new code/images and re-up
cd /opt/dojo && git pull && \
  docker compose --env-file .env -f deploy/compose/compose.yaml -f deploy/compose/compose.prod.yaml up -d --build

# Rollback: check out the previous commit and re-up
git log --oneline -5
git checkout <previous-sha>
docker compose --env-file .env -f deploy/compose/compose.yaml -f deploy/compose/compose.prod.yaml up -d --build
```

## Exercise

Do the HTTP-only variant first (`site_domain=":80"`, open `http://<ip>`), confirm it works,
then switch to the domain and watch Caddy's logs (`docker compose ... logs -f caddy`) issue
the certificate. Reading that ACME exchange once demystifies "automatic HTTPS".

## Checkpoint

- ✅ `http://<server-ip>` serves the app (HTTP test).
- ✅ With DNS + domain set, `https://<domain>` loads with a valid certificate.
- ✅ Only 80/443 are open publicly; 8080/5432 are not reachable from outside.

## Common failures

- Cert issuance fails → DNS `A` record not propagated yet, or ports 80/443 not open in the
  security group. Caddy logs show the ACME error.
- "context deadline exceeded" on ACME → the domain doesn't resolve to this server yet.

➡️ Next: [Lab 19 — Security hardening](../19-security/)

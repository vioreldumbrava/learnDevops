# Toolbox — set this up once

Two things stop the labs on this machine before anything else does, and one habit is worth
changing before you drill anything.

---

## 1. `kind` and `helm` are not installed

`kubectl` is on PATH (it ships with Docker Desktop). **`kind` and `helm` are not** — not in
PowerShell, not in the WSL distros. Every Kubernetes lab from 22 onward dies at
`kind: command not found` before it does anything interesting.

Fix it once, in WSL:

```bash
# kind
curl -Lo /tmp/kind https://kind.sigs.k8s.io/dl/latest/kind-linux-amd64
sudo install -m 0755 /tmp/kind /usr/local/bin/kind

# helm
curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# kubectl inside WSL (Docker Desktop's Windows binary works from PowerShell, not from bash)
curl -Lo /tmp/kubectl "https://dl.k8s.io/release/$(curl -Ls https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -m 0755 /tmp/kubectl /usr/local/bin/kubectl

kind version && helm version --short && kubectl version --client
```

kind talks to the Docker Desktop daemon through the WSL integration, so clusters you create in
bash are visible to `docker ps` in PowerShell and vice versa. There is one cluster, not two.

## 2. Give WSL enough memory

Docker Desktop has crashed mid-run on a **3-node kind cluster** with Cilium, Hubble and the full
Dojo stack. The daemon died; the kind containers survived and the cluster came back intact after
a Docker Desktop restart — worth knowing before you panic and delete anything.

Budget **≥8 GB** for WSL2 in `%UserProfile%\.wslconfig`:

```ini
[wsl2]
memory=8GB
processors=4
swap=4GB
```

Then `wsl --shutdown` and restart Docker Desktop.

**Tear one cluster down before creating the next.** `kind get clusters` first; running the
lab-22 cluster and the lab-48 three-node cluster at the same time is what gets you into trouble.

---

## 3. Drill in bash, not PowerShell

The labs are written PowerShell-first and that's fine — they're the reference. But every
**drill** ([DRILLS.md](DRILLS.md)) should run in WSL bash, for one blunt reason: the CKA exam
terminal is bash, and so is every server you'll touch in the job you're applying for. Muscle
memory built on `Select-String` and `$dc = "docker","compose",…` doesn't transfer to a Linux
box under exam pressure.

Put the exam reflexes in `~/.bashrc` now, so they're automatic by September:

```bash
alias k=kubectl
export do='--dry-run=client -o yaml'      # k create deploy web --image=nginx $do > web.yaml
export now='--force --grace-period=0'     # k delete pod x $now
source <(kubectl completion bash)
complete -o default -F __start_kubectl k

# vim, for the exam's YAML editing
cat >> ~/.vimrc <<'VIMRC'
set expandtab shiftwidth=2 tabstop=2
set number
VIMRC
```

The Dojo's own shorthand, bash version:

```bash
dc() { docker compose -f deploy/compose/compose.yaml "$@"; }
dcdev()  { dc -f deploy/compose/compose.dev.yaml "$@"; }
dcprod() { dc -f deploy/compose/compose.prod.yaml --env-file .env "$@"; }
dcobs()  { dc -f deploy/compose/compose.dev.yaml -f deploy/compose/compose.observability.yaml "$@"; }
```

The chaos injectors in [`scripts/chaos/`](../scripts/chaos/) are already bash-only, so lab 35 and
the weekly mock loop assume this setup anyway.

---

## 4. Everything else

Nothing else needs installing on the host — Go, Node, Python, `migrate` and `k6` all run inside
containers. Optional, only when their lab comes up:

| Tool | Needed by | Note |
|------|-----------|------|
| `terraform` | 16, 25, 39, 40 | |
| `ansible` | 17, 44 | Control node must be Linux/WSL, not PowerShell |
| `aws` CLI | 25, 40, 45 | Configure a profile before lab 25 |
| `cosign` | 41 | Keyless — no key material to manage |
| `psql` | 55 | Or just `dc exec db psql` |

Verify the whole set before a drill session rather than mid-drill:

```bash
for t in docker kubectl kind helm terraform ansible aws cosign; do
  printf '%-12s %s\n' "$t" "$(command -v $t || echo MISSING)"
done
```

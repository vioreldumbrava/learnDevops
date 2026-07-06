# Lab 48 — CKA exam readiness: cluster operations

**Maps to:** deepens labs 22–34 · **Milestone:** K8s deep-dive · **CKA**

## Concept

Labs 22–34 cover the *workloads-and-policy* half of the CKA: Deployments, Services, Ingress,
RBAC, NetworkPolicies, autoscaling, observability. The exam's other half is **cluster
administration** — and it's the half people fail on, because you can't learn it by deploying
apps: **etcd backup and restore**, **node operations** (cordon/drain against a
PodDisruptionBudget, a dead kubelet), **static pods**, **kubeadm**, and raw **kubectl speed**
(the exam is ~15–17 hands-on tasks in 120 minutes — typing YAML by hand loses).

The good news: a kind node is a container running real **kubeadm + systemd + kubelet +
containerd**, with the control plane as static pods — the same layout as a kubeadm-built
server. So every drill below is authentic, on a cluster you can delete without fear. That's
the point: *"has read about etcd restore"* and *"has done etcd restore"* are different skills,
and the exam (and the job) tests the second one.

## What you'll do

Create a disposable 3-node cluster, drill kubectl speed, back up **and restore** etcd for
real, drain a node against a PDB, break and fix the kubelet and a static pod, then sit a
timed 10-task mock exam.

## Steps

### 0. Throwaway cluster (3 nodes)

```powershell
kind create cluster --config deploy/k8s/kind/kind-cka.yaml
kubectl get nodes            # cka-control-plane, cka-worker, cka-worker2 — all Ready
```

kind switches your kubectl context to `kind-cka` automatically. In a multi-node kind cluster
the control-plane keeps its `NoSchedule` taint (like production), so your pods land on the
workers.

### 1. kubectl speed technique

The exam terminal has `k` aliased and completion installed. Train the same reflexes:

```bash
alias k=kubectl                                  # bash; PowerShell: Set-Alias k kubectl
export do="--dry-run=client -o yaml"             # k create deploy web --image=nginx $do > web.yaml
```

Never hand-write YAML — generate and edit:

```powershell
kubectl create deployment web --image=nginx --replicas=2 --dry-run=client -o yaml
kubectl run tmp --image=busybox --dry-run=client -o yaml -- sleep 3600
kubectl expose deployment web --port 80 --dry-run=client -o yaml
kubectl explain deployment.spec.strategy         # docs without leaving the terminal
```

Drill (target times — repeat until you beat them): pod with image+label **30s**, deployment
scaled + exposed **60s**, pod YAML generated to a file and edited **90s**.

### 2. etcd backup & restore (the task people fear most)

Everything the API server knows lives in etcd. Snapshot it, change the cluster, restore —
and watch the change vanish.

```powershell
# 2a. Snapshot, using the certs from etcd's own static-pod manifest. Save it under
#     /var/lib/etcd — that's a hostPath, so the file survives on the node.
kubectl -n kube-system exec etcd-cka-control-plane -- sh -c `
  'ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 --cacert=/etc/kubernetes/pki/etcd/ca.crt --cert=/etc/kubernetes/pki/etcd/server.crt --key=/etc/kubernetes/pki/etcd/server.key snapshot save /var/lib/etcd/snap.db'

kubectl -n kube-system exec etcd-cka-control-plane -- sh -c `
  'ETCDCTL_API=3 etcdctl snapshot status /var/lib/etcd/snap.db -w table'   # hash, keys, size

# 2b. Change the world AFTER the snapshot — this object should not survive the restore:
kubectl create configmap after-snapshot

# 2c. Restore the snapshot into a NEW data dir (inside /var/lib/etcd so it persists):
kubectl -n kube-system exec etcd-cka-control-plane -- sh -c `
  'ETCDCTL_API=3 etcdctl snapshot restore /var/lib/etcd/snap.db --data-dir /var/lib/etcd/restored'

# 2d. Point etcd at the restored dir: edit the static-pod manifest's hostPath on the node.
#     kubelet notices the change and restarts etcd; the API server blips for ~30-60s.
docker exec cka-control-plane sed -i `
  's|path: /var/lib/etcd$|path: /var/lib/etcd/restored|' /etc/kubernetes/manifests/etcd.yaml

# 2e. Wait for the API to come back, then prove the restore worked:
kubectl get configmap after-snapshot     # Error from server (NotFound) — time travel ✔
```

(`etcdctl snapshot status/restore` prints a deprecation warning pointing at `etcdutl` — fine
on the exam and here; the syntax is identical.)

### 3. Node ops: cordon, drain, and the PDB that says no

You met PodDisruptionBudgets in [deploy/k8s/base/pdb.yaml](../../deploy/k8s/base/pdb.yaml) —
the dojo's api/frontend must keep ≥1 pod through node drains. Feel what that protection
does from the operator's side:

```powershell
kubectl create deployment web --image=nginx:1.27-alpine --replicas=2
kubectl create poddisruptionbudget web --selector=app=web --min-available=2   # deliberately impossible
kubectl get pods -o wide                 # one pod per worker (control-plane is tainted)

kubectl drain cka-worker --ignore-daemonsets --delete-emptydir-data
# ...error: Cannot evict pod as it would violate the pod's disruption budget. (retries forever)
```

Evicting either pod would leave 1 available < `minAvailable: 2` → the eviction API refuses,
by design. Fix the budget, drain, undo:

```powershell
kubectl patch pdb web -p '{\"spec\":{\"minAvailable\":1}}'
kubectl drain cka-worker --ignore-daemonsets --delete-emptydir-data    # now succeeds
kubectl get pods -o wide                 # both replicas on cka-worker2
kubectl uncordon cka-worker
```

### 4. Break/fix: the kubelet dies

```powershell
docker exec cka-worker systemctl stop kubelet
kubectl get nodes -w                     # ~40s later: cka-worker NotReady (node-monitor grace)
```

Diagnose like on the exam — from the node, not from guesses:

```powershell
kubectl describe node cka-worker         # Conditions + "Kubelet stopped posting node status"
docker exec cka-worker systemctl status kubelet     # inactive (dead)  ← the smoking gun
docker exec cka-worker journalctl -u kubelet --no-pager -n 20
docker exec cka-worker systemctl start kubelet
kubectl get nodes -w                     # Ready again
```

(On a real server it's `ssh node` + the same `systemctl`/`journalctl` — kind just swaps ssh
for `docker exec`.)

### 5. Static pods: break/fix the scheduler

The control plane *is* static pods: the kubelet runs whatever lives in
`/etc/kubernetes/manifests`, no API server involved.

```powershell
docker exec cka-control-plane ls /etc/kubernetes/manifests   # etcd, apiserver, controller-manager, scheduler

docker exec cka-control-plane mv /etc/kubernetes/manifests/kube-scheduler.yaml /root/
kubectl -n kube-system get pods | findstr scheduler          # gone
kubectl create deployment orphan --image=nginx
kubectl get pods                                             # Pending — nobody schedules it

docker exec cka-control-plane mv /root/kube-scheduler.yaml /etc/kubernetes/manifests/
kubectl get pods                                             # Running — scheduler picked it up
```

### 6. Clean up

```powershell
kind delete cluster --name cka           # the whole point: practice on something disposable
```

## How it works

A kind "node" is a container whose PID 1 is **systemd**, running kubelet + containerd; kubeadm
inside it generated `/etc/kubernetes` exactly as on a cloud VM. That's why the three core
exam mechanics transfer 1:1: **etcd's data dir** is a hostPath the static-pod manifest points
at (restore = new dir + repoint), **NotReady** is almost always "kubelet stopped posting
status" (diagnose with systemctl/journalctl on the node), and **static pods** exist because
the control plane can't schedule itself — the kubelet watches a manifests directory instead.
Drain uses the **eviction API**, which is exactly the thing PDBs veto — voluntary disruptions
only; a crashing node ignores PDBs.

## kubeadm init/join/upgrade (the one thing kind can't drill)

kind bakes Kubernetes into the node image, so **cluster upgrades** need real VMs — or a free
hosted terminal:

- **Zero-install (recommended):** [killercoda.com/killer-shell-cka](https://killercoda.com/killer-shell-cka)
  — free interactive CKA scenarios including *cluster upgrade* and *kubeadm join*.
- **Local VMs (Multipass), the full experience:**
  ```text
  multipass launch -n cp -c 2 -m 2G && multipass launch -n w1 -c 2 -m 2G
  # on both: install containerd + kubeadm/kubelet/kubectl vX.Y, disable swap
  # cp:  sudo kubeadm init --pod-network-cidr=192.168.0.0/16   → install Calico
  # w1:  sudo kubeadm join <the exact command printed by init>
  # upgrade drill (control plane first, then worker):
  #   apt-get install kubeadm=X.(Y+1).*  → kubeadm upgrade plan → kubeadm upgrade apply vX.(Y+1)
  #   kubectl drain <node> → upgrade kubelet+kubectl → systemctl restart kubelet → uncordon
  ```
- **Booking the exam buys practice:** CKA registration currently includes **two killer.sh
  exam simulator sessions** (36h each) — harder than the real thing, the best calibration
  you can get. Book the exam *first*; a date beats an intention.

## Mock exam — 10 tasks, 45 minutes, timer on

Rules: kubernetes.io/docs allowed (as on the exam), nothing else. Do them in any order;
skip and return like on the real thing. Answers at the bottom — no peeking mid-run.

1. Namespace `drill`; in it a pod `web`, image `nginx:1.27-alpine`, label `tier=frontend`. *(2 min)*
2. Deployment `api` (image `nginx:1.27-alpine`), scale to 4, expose as ClusterIP service `api` on port 80. *(3 min)*
3. Generate into `sleeper.yaml` a pod running `busybox` with command `sleep 3600` — without writing YAML by hand — then create it. *(2 min)*
4. Take an etcd snapshot to `/var/lib/etcd/mock.db` and print its status table. *(5 min)*
5. Drain `cka-worker2` respecting PDBs. Something blocks you — identify it, fix it so at least one `web` replica stays available, finish the drain, then uncordon. *(6 min)*
6. `cka-worker` is NotReady (a colleague "cleaned up" a service on it). Find the cause and fix it. *(5 min)*
7. Prove the scheduler is a static pod: make it disappear, show a new pod stays `Pending`, bring it back. *(5 min)*
8. In `drill`: only pods labelled `role=client` (same namespace) may reach pod `web` on port 80; everything else denied. *(7 min)*
9. ServiceAccount `deployer` in `drill` that can `create`/`get` deployments **only** in `drill`; prove both the allow and a deny with `kubectl auth can-i`. *(7 min)*
10. Set deployment `api` to image `nginx:doesnotexist`, diagnose what you see, then roll back to the working revision. *(3 min)*

**Scoring:** 8+/10 inside 45 minutes → book the exam this week. 6–7 → redo labs 27/28 + steps
1–5 above and re-sit. ≤5 → work back through labs 22–34, this lab last.

<details>
<summary>Answers (open after the timer stops)</summary>

```bash
# 1
k create ns drill
k -n drill run web --image=nginx:1.27-alpine --labels=tier=frontend
# 2
k create deploy api --image=nginx:1.27-alpine --replicas=4
k expose deploy api --port 80
# 3
k run sleeper --image=busybox $do -- sleep 3600 > sleeper.yaml && k apply -f sleeper.yaml
# 4  — step 2 above, with snapshot save /var/lib/etcd/mock.db, then snapshot status ... -w table
# 5
k drain cka-worker2 --ignore-daemonsets --delete-emptydir-data   # blocked by PDB "web"
k patch pdb web -p '{"spec":{"minAvailable":1}}'                 # keep 1, allow eviction
k drain cka-worker2 --ignore-daemonsets --delete-emptydir-data && k uncordon cka-worker2
# 6
k describe node cka-worker                        # Kubelet stopped posting node status
docker exec cka-worker systemctl status kubelet   # dead → docker exec cka-worker systemctl start kubelet
# 7  — step 5 above (mv kube-scheduler.yaml out of /etc/kubernetes/manifests and back)
# 8
k -n drill apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: {name: web-allow-clients}
spec:
  podSelector: {matchLabels: {tier: frontend}}
  policyTypes: [Ingress]
  ingress:
  - from: [{podSelector: {matchLabels: {role: client}}}]
    ports: [{protocol: TCP, port: 80}]
EOF
# (kind's default CNI doesn't enforce it — lab 28 explains why Calico is needed; writing it is the exam skill)
# 9
k -n drill create sa deployer
k -n drill create role deployer --verb=create,get --resource=deployments
k -n drill create rolebinding deployer --role=deployer --serviceaccount=drill:deployer
k auth can-i create deployments -n drill --as=system:serviceaccount:drill:deployer   # yes
k auth can-i create deployments -n default --as=system:serviceaccount:drill:deployer # no
# 10
k set image deploy/api nginx=nginx:doesnotexist
k get pods            # ImagePullBackOff; rollout stuck (maxUnavailable protects the rest)
k rollout undo deploy/api && k rollout status deploy/api
```
</details>

## Exercise

Delete the cluster, recreate it, and re-run steps 1–5 **against the clock** — under 20
minutes total is exam-ready. Then do one full killercoda upgrade scenario so `kubeadm upgrade
plan/apply` isn't a first-time experience on exam day.

## Checkpoint

- ✅ `etcdctl snapshot status` shows the hash/keys table, and after the restore the
  `after-snapshot` ConfigMap is **gone**.
- ✅ You saw `Cannot evict pod ... disruption budget`, fixed the PDB, and the drain completed.
- ✅ You diagnosed NotReady via `systemctl`/`journalctl` (not by guessing) and fixed it.
- ✅ Mock exam: 8+/10 in 45 minutes — and the exam is **booked**.

## Common failures

- `etcdctl`: *context deadline exceeded* → wrong `--endpoints` or cert flags; copy the exact
  paths from `kubectl -n kube-system get pod etcd-cka-control-plane -o yaml` (they're in the
  livenessProbe/command).
- Restore "worked" but nothing changed → you restored to a directory *outside* the
  `/var/lib/etcd` hostPath (pod-local, vanished), or forgot to repoint the manifest (2d).
- Drain hangs forever → a PDB with `minAvailable` = current replicas (this lab's trap), or a
  bare pod that needs `--force`, or you forgot `--ignore-daemonsets`.
- Node still NotReady after `systemctl start kubelet` → give it the ~40s grace period;
  if it persists, `journalctl -u kubelet` — on real servers it's usually swap, certs, or
  containerd down.
- **Exam technique:** hand-writing YAML, not setting the `$do` alias, burning 15 minutes on
  one task instead of flagging and moving on. Speed is a trained skill — that's this lab.

➡️ This closes the CKA loop: labs 22–34 taught the objects, this lab teaches the *cluster*.
Book the exam, then continue the track: [docs/INTERVIEW_PREP.md](../../docs/INTERVIEW_PREP.md)
§6 (study plan) and §10 (mock-interview protocol).

# Lab 49 — Kubernetes networking deep dive (the data plane)

**Maps to:** deepens labs 22/28 · **Milestone:** K8s deep-dive · **Cert:** CKA/CKS

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

> ℹ️ **Order note:** the folder number is out of sequence on purpose (appended later, like
> lab 48). This belongs in the **Kubernetes deep-dive** and is best done right after
> [lab 22](../22-kubernetes/) (Services & Ingress) and alongside [lab 28](../28-k8s-network-policies/)
> (NetworkPolicies). [CURRICULUM.md](../../docs/CURRICULUM.md) shows the intended order.

## Concept

You've *used* Kubernetes networking since lab 22 — Services, DNS names, an Ingress — but it's
been a black box: you type `api:8080` and it works. This lab opens the box. Kubernetes
networking rests on three rules and a lot of kernel plumbing:

1. **Every pod gets its own IP**, and every pod can reach every other pod **without NAT** — one
   flat network. (The CNI plugin makes this true; on kind it's kindnet, or Calico in lab 28.)
2. **A Service is a stable virtual IP** in front of a changing set of pods. It is *not* a
   process — it's **kube-proxy** programming the node's kernel (iptables/IPVS) to rewrite
   packets aimed at the virtual IP toward a real pod IP.
3. **DNS (CoreDNS)** turns names into those virtual IPs, so nothing hardcodes an address.

By the end you'll have *seen* each one on the node: the network namespace a pod lives in, the
kernel rules kube-proxy wrote, and the DNS records CoreDNS serves. This is core CKA/CKS
material and one of the most common senior-interview areas — "walk me through how a request
reaches a pod" is a question you'll be able to answer from memory *and* from having watched it.

## What you'll do

On the lab-22 kind cluster, trace a packet through all five layers — pod sandbox → flat pod
network → ClusterIP/kube-proxy → CoreDNS → Ingress — inspecting the real kernel state at each
hop, then run the "the Service returns nothing" troubleshooting decision tree.

## Setup

The lab-22 stack running on kind (namespace `devops-dojo`, api/frontend/db up). If it isn't:

```powershell
# See deploy/k8s/README.md for the full walkthrough. In short:
kind create cluster --config deploy/k8s/kind/kind-cluster.yaml
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml
kubectl wait -n ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=120s
docker build -t devops-dojo/api:dev ./app/api; docker build -t devops-dojo/frontend:dev ./app/frontend
kind load docker-image devops-dojo/api:dev devops-dojo/frontend:dev
kubectl apply -f deploy/k8s/base/namespace.yaml
kubectl create configmap dojo-migrations -n devops-dojo --from-file=db/migrations/
kubectl apply -f deploy/k8s/base/
kubectl -n devops-dojo wait --for=condition=available deploy/api deploy/frontend --timeout=180s
```

A single-node kind cluster is named `kind-control-plane` as a container — that's the "node" we
`docker exec` into to see the kernel state (same trick as [lab 48](../48-cka-exam-readiness/)).
Give the frontend/nginx pod (it has a shell + `wget`/`nslookup`) a shortcut:

```powershell
$fe = kubectl -n devops-dojo get pod -l app=frontend -o jsonpath="{.items[0].metadata.name}"
```

## Steps

### 1. The pod sandbox: where the "pod IP" actually lives

A pod's containers share one **network namespace**, held open by a tiny **`pause` container** —
that's the thing that owns `eth0` and the pod IP; your app container just joins it. Find it:

```powershell
# Every pod IP is on the flat pod network (10.244.x.x on kindnet):
kubectl -n devops-dojo get pods -o wide

# On the node, list sandboxes — one pause container per pod:
docker exec kind-control-plane crictl pods | findstr devops-dojo

# The pod's eth0 is one end of a veth PAIR; the other end is on the node.
kubectl -n devops-dojo exec $fe -- ip -4 addr show eth0     # the pod IP + "@ifN" peer index
kubectl -n devops-dojo exec $fe -- ip route                 # default route -> the node bridge

# The matching veth on the NODE side (its name pairs with the @ifN above):
docker exec kind-control-plane ip link | findstr veth
```

*Aha:* delete-and-recreate an app container and the pod IP survives — because the IP belongs to
the **sandbox**, not your app. That's also why a crashlooping app keeps its IP.

### 2. The flat network: pods talk directly, no NAT

```powershell
$apiIP = kubectl -n devops-dojo get pod -l app=api -o jsonpath="{.items[0].status.podIP}"
kubectl -n devops-dojo exec $fe -- wget -qO- --timeout=3 http://${apiIP}:8080/healthz
#   ok    <- one pod reached another by raw IP, through no Service at all
```

The reply came back with the source pod's real IP (no source-NAT between pods). The node's
routing table + the CNI are what make any pod IP reachable from any node.

*Aha:* Services aren't what make pods reachable — the network is **already flat**. Services
solve a *different* problem: pod IPs are ephemeral (step 1's survivor gets a new IP when
rescheduled), so you need a **stable** address. That's next.

### 3. ClusterIP = a virtual IP the kernel rewrites

```powershell
# The Service has a stable ClusterIP; the pods behind it are listed in an EndpointSlice.
kubectl -n devops-dojo get svc api                       # CLUSTER-IP e.g. 10.96.x.x
kubectl -n devops-dojo get endpointslices -l kubernetes.io/service-name=api -o wide
#   ENDPOINTS = the current api pod IPs (compare to `get pods -o wide`)

# The ClusterIP is FICTION: nothing answers ICMP, yet TCP works —
kubectl -n devops-dojo exec $fe -- sh -c "ping -c1 -W1 api >/dev/null 2>&1; echo ping=$?; wget -qO- --timeout=3 http://api:8080/healthz"
#   ping=1   (no host owns the VIP)      ok   (the kernel DNAT'd the connection)

# See the rules kube-proxy wrote. Find the api ClusterIP, then grep the node's iptables:
$cip = kubectl -n devops-dojo get svc api -o jsonpath="{.spec.clusterIP}"
docker exec kind-control-plane iptables-save -t nat | findstr $cip
docker exec kind-control-plane sh -c "iptables-save -t nat | grep -A3 KUBE-SVC"   # the SVC->EP chains
```

You'll see a `KUBE-SERVICES` rule for the ClusterIP jumping to a `KUBE-SVC-…` chain, which
uses `statistic --probability` to spread connections across `KUBE-SEP-…` chains — one per
endpoint — each doing `DNAT` to a pod IP. **That is load balancing**: it's `iptables`, in the
kernel, not a proxy process in the path.

Watch it react to reality:

```powershell
kubectl -n devops-dojo scale deploy/api --replicas=3
kubectl -n devops-dojo get endpointslices -l kubernetes.io/service-name=api -o jsonpath="{.items[*].endpoints[*].addresses[*]}"
docker exec kind-control-plane sh -c "iptables-save -t nat | grep KUBE-SEP | wc -l"   # more SEP chains now
kubectl -n devops-dojo scale deploy/api --replicas=1
```

*Aha:* the ClusterIP never changes, but the DNAT targets do — the endpoint controller keeps the
EndpointSlice in sync with ready pods, and kube-proxy keeps the kernel in sync with the
EndpointSlice. **Readiness probes gate this**: a not-ready pod is pulled from the slice, so no
traffic is DNAT'd to it (that's the lab-08 readiness probe, seen from the network side).

### 4. CoreDNS: names → those virtual IPs

```powershell
# Pods are handed CoreDNS as their resolver, with search domains that let short names work:
kubectl -n devops-dojo exec $fe -- cat /etc/resolv.conf
#   nameserver 10.96.0.10
#   search devops-dojo.svc.cluster.local svc.cluster.local cluster.local

# Resolve the api Service — the A record IS the ClusterIP from step 3:
kubectl -n devops-dojo exec $fe -- nslookup api.devops-dojo.svc.cluster.local
kubectl -n devops-dojo get svc api -o jsonpath="{.spec.clusterIP}"    # same value

# The db Service is HEADLESS (clusterIP: None) — DNS returns POD IPs, not a VIP:
kubectl -n devops-dojo exec $fe -- nslookup db.devops-dojo.svc.cluster.local
kubectl -n devops-dojo get pod -l app=db -o jsonpath="{.items[*].status.podIP}"   # the same IP(s)
```

Break it, to feel how much rides on DNS:

```powershell
kubectl -n kube-system scale deploy/coredns --replicas=0
kubectl -n devops-dojo exec $fe -- sh -c "nslookup api 2>&1 | head -3; echo ---; wget -qO- --timeout=3 http://api:8080/healthz || echo 'name lookup FAILED'"
kubectl -n kube-system scale deploy/coredns --replicas=2       # restore
```

*Aha:* the short name `api` works because of the **search domains**; `api` → `api.devops-dojo.svc.cluster.local`
→ the ClusterIP → (step 3) a pod. Headless services skip the VIP entirely and hand back pod IPs —
which is exactly why StatefulSets use them to address individual replicas (`db-0`, `db-1`). This
is also the mechanism lab 28's `allow-dns` policy protects: block egress to CoreDNS and *every*
name breaks.

### 5. Service types: layers, not alternatives

```powershell
kubectl apply -f deploy/k8s/networking/service-types.yaml
kubectl -n devops-dojo get svc -l demo=service-types
```

| Type | What it adds | Reach it | Use when |
|------|--------------|----------|----------|
| **ClusterIP** (default) | a virtual IP + kube-proxy DNAT (step 3) | in-cluster only | service-to-service (the norm) |
| **NodePort** | ClusterIP **+ a static port on every node** | `<nodeIP>:30080` | bare-metal / behind your own LB |
| **LoadBalancer** | NodePort **+ a cloud LB** provisioned for it | external IP | cloud (EKS/AKS); **stays `<pending>` on kind** — no cloud to call |
| **ExternalName** | *nothing in the data plane* — a CNAME in CoreDNS | in-cluster name → external host | point in-cluster code at RDS etc. (lab 40) |
| **headless** (`clusterIP: None`) | **removes** the VIP — DNS returns pod IPs | per-pod DNS | StatefulSets, client-side LB |

```powershell
# NodePort — kube-proxy added a rule catching the node port; kind maps 30080 out:
docker exec kind-control-plane sh -c "iptables-save -t nat | grep 30080"
# ExternalName is pure DNS — a CNAME, no endpoints:
kubectl -n devops-dojo exec $fe -- nslookup external-db.devops-dojo.svc.cluster.local | findstr -i "canonical name"
kubectl -n devops-dojo get endpointslices -l kubernetes.io/service-name=external-db   # none — nothing to proxy
# LoadBalancer on kind stays pending (documented, not a bug):
kubectl -n devops-dojo get svc | findstr pending
```

*Aha:* NodePort and LoadBalancer are **built on** ClusterIP — each type adds one layer of reach,
it doesn't replace the mechanism underneath.

### 6. The Ingress data path, end to end

Now trace the *real* request you make in a browser — `http://localhost/api/steps`:

```powershell
# localhost:80 -> kind extraPortMapping -> the ingress-nginx controller POD:
kubectl -n ingress-nginx get pods -o wide
kubectl -n ingress-nginx get svc ingress-nginx-controller

# The controller turns your Ingress object into an nginx upstream config —
# read it: the upstream is the api Service's ENDPOINTS (pod IPs), not the VIP:
$ic = kubectl -n ingress-nginx get pod -l app.kubernetes.io/component=controller -o jsonpath="{.items[0].metadata.name}"
kubectl -n ingress-nginx exec $ic -- sh -c "cat /etc/nginx/nginx.conf | grep -A8 'devops-dojo-api'"

# Follow the whole path with one request:
curl -s http://localhost/api/steps | head -c 120
```

The full chain: **client → localhost:80 (kind port map) → ingress-nginx pod → (it load-balances
straight to) api pod IPs from the EndpointSlice → your Go app → Postgres.** ingress-nginx
deliberately talks to pod IPs directly (it watches EndpointSlices itself) rather than through the
ClusterIP, so it can do its own load balancing and session affinity.

*Aha:* this is the **in-cluster second half** of the "what happens when you type a URL" story in
[INTERVIEW_PREP.md](../../docs/INTERVIEW_PREP.md) §8. You can now narrate a packet from the
browser all the way to a database row.

## How it works (the one-paragraph mental model)

CNI gives every pod an IP on one flat network (step 1–2). A Service is a **stable virtual IP**
that the **endpoint controller** (which writes EndpointSlices from ready pods) and **kube-proxy**
(which writes kernel DNAT rules from those slices) keep pointed at live pods (step 3).
**CoreDNS** maps names to those virtual IPs, with search domains making short names work (step
4). **Service types** stack extra reach on top of ClusterIP; headless opts out of the VIP (step
5). An **Ingress controller** is just a reverse proxy that watches EndpointSlices and forwards to
pod IPs (step 6). Every layer is *desired state → a controller → kernel/DNS state*, the same
reconcile pattern as everything else in Kubernetes.

## Exercise — the "Service returns nothing" decision tree

The single most common K8s networking incident, and a favorite interview scenario. Break it and
walk the tree:

```powershell
# Inject: make the api pods fail readiness (a common real cause — bad probe/dependency).
kubectl -n devops-dojo patch deploy api --type=json `
  -p='[{"op":"replace","path":"/spec/template/spec/containers/0/readinessProbe/httpGet/path","value":"/nope"}]'
kubectl -n devops-dojo rollout status deploy/api --timeout=60s
kubectl -n devops-dojo exec $fe -- sh -c "wget -qO- --timeout=3 http://api:8080/healthz || echo DOWN"
```

Diagnose in order — each command isolates one layer:

1. **DNS?** `kubectl exec $fe -- nslookup api` — resolves? (CoreDNS/search domains) → yes, so not DNS.
2. **Endpoints?** `kubectl -n devops-dojo get endpointslices -l kubernetes.io/service-name=api` —
   **empty!** No ready pods → the Service has nothing to DNAT to. That's the cause.
3. **Why no endpoints?** `kubectl -n devops-dojo get pods -l app=api` → `READY 0/1`;
   `kubectl describe pod` → readiness probe failing on `/nope`.

```powershell
# Fix and confirm the endpoint (and traffic) come back:
kubectl -n devops-dojo patch deploy api --type=json `
  -p='[{"op":"replace","path":"/spec/template/spec/containers/0/readinessProbe/httpGet/path","value":"/readyz"}]'
kubectl -n devops-dojo rollout status deploy/api --timeout=60s
kubectl -n devops-dojo get endpointslices -l kubernetes.io/service-name=api   # populated again
```

Write the tree in your notes — **DNS → Service/Endpoints → kube-proxy → pod** — it's the answer
to "a Service isn't responding, what do you check?" and it mirrors lab 35's method.

## Checkpoint

- ✅ You found a pod's `pause` sandbox and its `veth` pair on the node.
- ✅ You reached one pod from another by raw IP (flat network, no NAT).
- ✅ You showed the ClusterIP answers TCP but not ping, and read the kube-proxy **DNAT** chains
  that make that true — and watched them change when you scaled.
- ✅ You resolved a Service name to its ClusterIP via CoreDNS, and a headless name to pod IPs;
  scaling CoreDNS to 0 broke name resolution.
- ✅ You demonstrated ClusterIP vs NodePort vs LoadBalancer(pending) vs ExternalName vs headless.
- ✅ You traced a browser request through ingress-nginx to a pod, and ran the "no endpoints"
  decision tree.

## Common failures

- `crictl`/`iptables-save` "not found" → run them **inside the node** (`docker exec
  kind-control-plane …`), not on your host; kind ships them in the node image.
- iptables grep returns nothing → your kube-proxy is in **IPVS** mode (some clusters): use
  `docker exec kind-control-plane ipvsadm -Ln` instead. Default kind is iptables mode.
- `nslookup`/`ping` "not found" in a pod → the distroless **api** pod has no shell; run network
  probes from the **frontend** pod (`$fe`), which is nginx/BusyBox.
- LoadBalancer stuck `<pending>` → **expected** on kind (no cloud LB). On EKS/AKS it gets a real
  address; `metallb` provides one on bare metal.
- After scaling CoreDNS back up, names still fail for a few seconds → DNS caches; retry.

## Where to go next

- **Cilium / eBPF**: modern CNIs replace the iptables DNAT you saw here with eBPF programs
  (faster at scale, better observability). Same *concept*, different data plane — install Cilium
  on a kind cluster and re-run step 3 to compare.
- **Service mesh** (Istio/Linkerd): a sidecar/ambient layer that adds mTLS, L7 routing and
  traffic mirroring *on top of* this — [CURRICULUM.md](../../docs/CURRICULUM.md) explains why the
  Dojo deliberately doesn't need one. Now you can articulate exactly what it would add.

➡️ Back to the map: [docs/CURRICULUM.md](../../docs/CURRICULUM.md). This closes the networking
loop: lab 22 used it, lab 28 secured it, **lab 49 explains it**.

# Lab 51 — Cilium: eBPF networking, Hubble, L7 policy & Gateway API

**Maps to:** deepens labs 28/49 · **Milestone:** K8s deep-dive · **Cert:** CKA/CKS

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

> ℹ️ **Order note:** the folder number is out of sequence on purpose (appended later, like
> labs 48/49). This belongs in the **Kubernetes deep-dive**, right after
> [lab 49](../49-k8s-networking-deep-dive/) (whose iptables data plane this lab replaces) and
> with [lab 28](../28-k8s-network-policies/) (NetworkPolicies) fresh in mind.
> [CURRICULUM.md](../../docs/CURRICULUM.md) shows the intended order.

## Concept

Lab 49 ended with a claim worth testing: *kube-proxy's iptables DNAT is just one implementation
of the Service contract*. This lab installs the other one. **Cilium** replaces both the CNI
**and** kube-proxy with **eBPF** — small programs the kernel runs at the network hooks — and
because it owns the whole data path, it can do things iptables never could:

1. **Kube-proxy-free Services** — ClusterIP lookups become a BPF hash-map hit (often resolved at
   `connect()` time, before a packet exists), not a walk down `KUBE-SVC` chains.
2. **Identity-based policy up to L7** — rules match *labels*, not IPs, and can say "frontend may
   only **GET** from the api" — enforced by a node-local Envoy the CNI manages. Lab 28's Calico
   polices *connections*; Cilium polices *requests*.
3. **Hubble** — every flow, with Kubernetes identities attached, observable live.
4. **Gateway API** — the successor to Ingress, implemented by the CNI itself, with **LB-IPAM**
   handing out real LoadBalancer IPs (the thing that stayed `<pending>` in lab 49).

The three rules of Kubernetes networking (flat pod network, Services as stable VIPs, DNS) don't
change — only the engine underneath. This is the engine you'll actually meet in managed clouds:
GKE Dataplane V2 *is* Cilium, Azure CNI is "powered by Cilium", and it's a common EKS choice —
"kindnet → Calico → Cilium" is a CNI progression you can now narrate from experience.

## What you'll do

On a fresh 3-node kind cluster with **no default CNI and no kube-proxy**, install Cilium via
Helm, deploy the same app, and re-run lab 49's proofs against eBPF maps instead of iptables;
watch flows with Hubble; push lab 28's zero-trust policy to L7 (deny a POST with a **403**, not
a timeout); then run the app's Gateway + HTTPRoute on Cilium with a real LoadBalancer IP.

## Setup

You need `helm` (lab 23) and about **8 GB** free for Docker Desktop/WSL2 — three nodes plus
Cilium, Envoy, Hubble and the app (first-time image pulls are ~1 GB; give the install a few
minutes). The dojo cluster from lab 22 can stay up: this cluster maps no host ports.

```powershell
kind create cluster --config deploy/k8s/kind/kind-cilium.yaml
kubectl get nodes    # all NotReady — EXPECTED: there is no CNI yet, kubelet says so
```

## Steps

### 1. A cluster with no kube-proxy at all

Install the Gateway API CRDs **first** — the Cilium operator checks for them at startup and
silently skips Gateway support if they're missing (step 5 would have no `cilium` GatewayClass):

```powershell
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.4.1/standard-install.yaml

# Now Cilium itself. Read deploy/k8s/cilium/values.yaml first — every key is a decision:
helm repo add cilium https://helm.cilium.io
helm install cilium cilium/cilium --version 1.19.5 -n kube-system -f deploy/k8s/cilium/values.yaml
kubectl -n kube-system rollout status ds/cilium --timeout=300s
kubectl get nodes    # Ready — the CNI arrived, kubelet is satisfied
```

Now prove what this cluster *doesn't have*:

```powershell
kubectl -n kube-system get ds kube-proxy
#   Error from server (NotFound) — the "mandatory" DaemonSet simply isn't there

# Lab 49 step 3 found KUBE-SVC/KUBE-SEP DNAT chains on the node. Count them here:
docker exec cilium-control-plane sh -c "iptables-save -t nat | grep -c KUBE-SVC"
#   0    (a few CILIUM_* chains exist for plumbing, but NO per-service rules)

kubectl -n kube-system exec ds/cilium -- cilium-dbg status --brief
#   OK   (the agent's one-line health summary; drop --brief for the full picture)

# And the agent says so itself — who is doing kube-proxy's job, and is L7 ready:
kubectl -n kube-system exec ds/cilium -- cilium-dbg status | findstr /c:"KubeProxyReplacement" /c:"Proxy Status" /c:"Cilium:"
#   KubeProxyReplacement:    True   [eth0  172.18.0.2 … (Direct Routing)]
#   Cilium:                  Ok   1.19.5 …
#   Proxy Status:            OK, ip 10.244.0.172, 0 redirects active on ports 10000-20000
```

*Aha:* kube-proxy was never *the* Service implementation — it's the **default** one. The
Service/EndpointSlice objects, the DNS names, the app manifests: all unchanged. The contract
survives; the implementer changed.

### 2. Same Services, new engine: read the eBPF map instead of iptables

Deploy the same stack as labs 22/49—note `--name cilium` on the image load. Do not install an
extra traffic controller: Gateway API is already the supported base path, and Cilium will
reconcile it in step 5. The Gateway can exist before its class/controller is ready.

```powershell
docker build -t devops-dojo/api:dev ./app/api; docker build -t devops-dojo/frontend:dev ./app/frontend
kind load docker-image devops-dojo/api:dev devops-dojo/frontend:dev --name cilium
kubectl apply -f deploy/k8s/base/namespace.yaml
kubectl create configmap dojo-migrations -n devops-dojo --from-file=db/migrations/
# Apply the app workloads, but not base/gateway.yaml or base/httproute.yaml.
# Those belong to Envoy Gateway (`EnvoyProxy` is an Envoy-specific CRD); this
# cluster deliberately uses Cilium's Gateway implementation in step 5.
kubectl apply `
  -f deploy/k8s/base/configmap.yaml `
  -f deploy/k8s/base/secret.yaml `
  -f deploy/k8s/base/postgres-statefulset.yaml `
  -f deploy/k8s/base/redis.yaml `
  -f deploy/k8s/base/api.yaml `
  -f deploy/k8s/base/frontend.yaml `
  -f deploy/k8s/base/worker.yaml `
  -f deploy/k8s/base/hpa.yaml `
  -f deploy/k8s/base/pdb.yaml `
  -f deploy/k8s/base/migrate-job.yaml
kubectl -n devops-dojo wait --for=condition=available deploy/api deploy/frontend --timeout=180s
$fe = kubectl -n devops-dojo get pod -l app=frontend -o jsonpath="{.items[0].metadata.name}"
```

Re-run lab 49's ClusterIP proof — identical behavior, then look where the *new* rules live:

```powershell
# NOTE the SINGLE quotes: in double quotes PowerShell would expand $? itself and
# you'd get "ping=True" instead of the shell's exit code.
kubectl -n devops-dojo exec $fe -- sh -c 'ping -c1 -W1 api >/dev/null 2>&1; echo ping=$?; wget -qO- --timeout=3 http://api:8080/healthz'
#   ping=1
#   {"status":"ok"}     <- the VIP is still fiction: no host answers ICMP, yet TCP works

# In lab 49 the next move was iptables-save | findstr <ClusterIP>. Try it:
$cip = kubectl -n devops-dojo get svc api -o jsonpath="{.spec.clusterIP}"
docker exec cilium-control-plane sh -c "iptables-save -t nat | grep $cip || echo 'not in iptables'"
#   not in iptables

# The service table now lives in BPF maps, read through the agent. Print the WHOLE
# list (it's short) and find the api ClusterIP — don't pipe it through findstr:
# extra backends are printed on CONTINUATION lines that a line filter would hide.
kubectl -n kube-system exec ds/cilium -- cilium-dbg service list
#   ID   Frontend                Service Type   Backend
#   …
#   10   10.96.154.90:8080/TCP   ClusterIP      1 => 10.244.1.228:8080/TCP (active)
#                                               2 => 10.244.2.154:8080/TCP (active)
#   14   172.18.255.192:80/TCP   LoadBalancer                    <- step 5, later

kubectl -n kube-system exec ds/cilium -- cilium-dbg bpf lb list | findstr $cip
#   the same mapping straight out of the BPF map — the DNAT decision as a hash entry
```

Watch it react to scaling, exactly like lab 49 did with `KUBE-SEP` chains (the api
Deployment sits behind an HPA with `minReplicas: 2`, so 2 backends is its floor):

```powershell
kubectl -n devops-dojo scale deploy/api --replicas=3
kubectl -n devops-dojo rollout status deploy/api --timeout=120s
kubectl -n kube-system exec ds/cilium -- cilium-dbg service list
#   10   10.96.154.90:8080/TCP   ClusterIP      1 => 10.244.1.228:8080/TCP (active)
#                                               2 => 10.244.2.118:8080/TCP (active)
#                                               3 => 10.244.2.154:8080/TCP (active)
kubectl -n devops-dojo scale deploy/api --replicas=2
```

*Aha:* the control loop is **identical** to lab 49 — endpoint controller → EndpointSlice →
agent → kernel. Only the last hop changed: a per-packet walk down iptables chains (cost grows
with service count) became an O(1) map lookup — and with socket-level load balancing the
"DNAT" often happens at `connect()`, so the wire never even sees the ClusterIP.

### 3. Hubble: the network, narrated

Lab 49 *inferred* traffic from iptables counters and probes. Hubble just shows it to you.

One thing to get right first, or half your flows will be invisible: each agent records only
**its own node's** traffic. **hubble-relay** (installed by `values.yaml`) aggregates all three.
The `hubble` CLI ships inside the agent pod, so point it at the relay — by **ClusterIP**, since
the agent runs host-networked and can't resolve cluster DNS names:

```powershell
$relay = kubectl -n kube-system get svc hubble-relay -o jsonpath="{.spec.clusterIP}"

# Generate a request, then read the flows it produced (cluster-wide):
kubectl -n devops-dojo exec $fe -- wget -qO- --timeout=3 http://api:8080/api/steps > $null
kubectl -n kube-system exec ds/cilium -- hubble observe --server ${relay}:80 --namespace devops-dojo --last 20
#   devops-dojo/frontend-…:58387 (ID:8286) -> kube-system/coredns-…:53 (ID:31617) dns-request proxy FORWARDED (DNS Query api.devops-dojo.svc.cluster.local. A)
#   devops-dojo/frontend-…:58387 (ID:8286) <- kube-system/coredns-…:53 (ID:31617) dns-response proxy FORWARDED (DNS Answer "10.96.154.90" TTL: 30 …)
#   devops-dojo/frontend-…:40908 (ID:8286) -> devops-dojo/api-…:8080 (ID:60025) to-overlay FORWARDED (TCP Flags: SYN)
```

Every line names **identities** (`ID:8286` = the frontend's label set), not just IPs — and the
DNS lookup you never think about is right there in the middle, resolved to the ClusterIP from
step 2. For the live service map:

```powershell
kubectl -n kube-system port-forward svc/hubble-ui 12000:80
# browse http://localhost:12000 → namespace devops-dojo: the app's real traffic graph
```

*Aha:* this is tcpdump-grade visibility with Kubernetes context attached — the answer to "how
do you debug pod-to-pod traffic?" that doesn't start with "install tcpdump in the pod". It
falls out of eBPF for free: the datapath already sees every packet; Hubble just keeps notes.
Note the split you just worked around: the **agent** sees one node, the **relay** sees the
cluster. Query the wrong one and a flow that definitely happened simply isn't there.

### 4. L7 policy: deny a POST with a 403, not a timeout

Read [deploy/k8s/cilium/cnp-l7.yaml](../../deploy/k8s/cilium/cnp-l7.yaml) next to lab 28's
[network-policies.yaml](../../deploy/k8s/network-policies/network-policies.yaml) — same
whitelist idea, two upgrades: no namespace-wide default-deny object needed (selecting an
endpoint for a direction *makes* it default-deny for that direction), and rules climb from
ports to **HTTP methods and paths**. Apply and probe:

```powershell
kubectl apply -f deploy/k8s/cilium/cnp-l7.yaml

# GETs are allowed:
kubectl -n devops-dojo exec $fe -- wget -qO- --timeout=3 http://api:8080/api/steps > $null; echo "GET: $LASTEXITCODE"
#   GET: 0

# A POST to the same service, same port, same pod — denied AT THE REQUEST level:
kubectl -n devops-dojo exec $fe -- sh -c "wget -O- -T3 --post-data='{}' http://api:8080/api/notes 2>&1 | head -2"
#   wget: server returned error: HTTP/1.1 403 Forbidden
```

Look closely at what just happened: the TCP connection **succeeded** and something answered
HTTP — but it wasn't the Go app, it was the Envoy proxy Cilium put in the path. In lab 28 a
denied flow just hung until timeout (dropped packets, L3/4). Here denial is a *protocol-level
answer*. And identity still gates at L3/4 first — from a pod without the `app: frontend` label,
even a GET never connects:

```powershell
kubectl -n devops-dojo run tmp --image=busybox:1.36 --restart=Never --rm -it -- wget -qO- -T3 http://api:8080/api/steps
#   wget: download timed out    <- dropped at L3/4: wrong identity, no HTTP answer at all
```

Watch both verdicts in Hubble — L7 flows carry the method, path **and status code**. Use the
relay from step 3: ingress policy is enforced on whichever node the *destination* api pod
happens to be on, and with an HPA moving replicas around, a single agent will miss half of it:

```powershell
kubectl -n kube-system exec ds/cilium -- hubble observe --server ${relay}:80 --namespace devops-dojo --protocol http --last 10
#   … -> …/api-…:8080 http-request  FORWARDED (HTTP/1.1 GET  http://api:8080/api/steps)
#   … <- …/api-…:8080 http-response FORWARDED (HTTP/1.1 200 2ms (GET http://api:8080/api/steps))
#   … -> …/api-…:8080 http-request  DROPPED   (HTTP/1.1 POST http://api:8080/api/notes)
#   … <- …/api-…:8080 http-response FORWARDED (HTTP/1.1 403 0ms (POST http://api:8080/api/notes))

kubectl -n kube-system exec ds/cilium -- hubble observe --server ${relay}:80 --namespace devops-dojo --verdict DROPPED --last 10
#   devops-dojo/tmp:38650 (ID:63398) <> devops-dojo/api-…:8080 Policy denied DROPPED (TCP Flags: SYN)
#   devops-dojo/frontend-… (ID:8286) -> devops-dojo/api-…:8080 http-request DROPPED (HTTP/1.1 POST …/api/notes)
```

Read those last two lines together — they are the whole lesson. The `tmp` pod is dropped at
**SYN**, before a request exists (`Policy denied`, wrong identity). The frontend's POST is
dropped as an **http-request**, after the connection succeeded, and gets a 403 written back.

*Aha:* Calico (lab 28) polices **connections**; Cilium polices **requests** — via a proxy the
CNI injected transparently: no sidecar, no app change, no service mesh installed. The DNS rule
in `frontend-egress` does the same for lookups: `hubble observe --protocol dns` shows every
query by name — tighten `matchPattern` and you have DNS-name egress allowlisting, which plain
NetworkPolicy cannot express at all.

### 5. Gateway API: the successor to Ingress, with a real LoadBalancer IP

Ingress crammed listener config, routing and controller-specific annotations into one object.
**Gateway API** splits the roles: a `Gateway` (platform team: "an HTTP entry point on :80") and
`HTTPRoute`s (app team: "these paths to these Services"). Cilium implements it natively — check
the class the operator registered when it found the CRDs from step 1:

```powershell
kubectl get gatewayclass
#   NAME     CONTROLLER                     ACCEPTED
#   cilium   io.cilium/gateway-controller   True
```

A Gateway needs an IP. On kind, LoadBalancer meant `<pending>` in lab 49 — now read
[lb-ipam-pool.yaml](../../deploy/k8s/cilium/lb-ipam-pool.yaml) (Cilium assigns IPs from a pool)
and [l2-announcement.yaml](../../deploy/k8s/cilium/l2-announcement.yaml) (nodes answer ARP for
them), check the pool matches your docker network, and apply the lot:

```powershell
docker network inspect kind --format "{{range .IPAM.Config}}{{.Subnet}} {{end}}"
#   fc00:f853:ccd:e793::/64 172.18.0.0/16
#   Take the IPv4 one. (Don't index [0] — on Docker Desktop that's the IPv6 subnet.)
#   If yours isn't 172.18.0.0/16, edit the cidr in lb-ipam-pool.yaml to a slice of it.

kubectl apply -f deploy/k8s/cilium/lb-ipam-pool.yaml
kubectl apply -f deploy/k8s/cilium/l2-announcement.yaml
kubectl apply -f deploy/k8s/cilium/gateway.yaml
kubectl apply -f deploy/k8s/cilium/httproute.yaml

kubectl -n devops-dojo get gateway dojo-gw
#   NAME      CLASS    ADDRESS          PROGRAMMED
#   dojo-gw   cilium   172.18.255.194   True        <- a real address, on kind
kubectl -n devops-dojo get svc cilium-gateway-dojo-gw
#   TYPE=LoadBalancer, EXTERNAL-IP set — the exact thing lab 49 showed as <pending>
```

Prove it routes. One catch: on Docker Desktop the kind bridge isn't routable from Windows
itself, so probe from a throwaway container **on that network** (same idea as lab 49's
`docker exec` proofs — stand where the network can see you):

```powershell
$gwip = kubectl -n devops-dojo get gateway dojo-gw -o jsonpath="{.status.addresses[0].value}"
docker run --rm --network kind curlimages/curl:8.11.0 -s http://$gwip/healthz
#   ok                                          <- /healthz routed to the api
docker run --rm --network kind curlimages/curl:8.11.0 -s -o /dev/null -w "%{http_code}`n" http://$gwip/
#   200                                         <- / routed to the frontend
docker run --rm --network kind curlimages/curl:8.11.0 -s -X POST -d '{\"completed\":true}' http://$gwip/api/progress/00-prerequisites
#   {"completed":true,"step_id":"00-prerequisites"}   <- and POSTs work THROUGH THE GATEWAY…
```

…because Gateway traffic reaches the api with the reserved identity `ingress`, which
`cnp-l7.yaml` allows at L4 — while the same POST from the frontend pod got a 403 in step 4.
One policy file, three different outcomes by *who is asking*.

*Aha:* `<pending>` never meant "kind can't do LoadBalancers" — it meant *nobody here implements
them*. LB-IPAM + L2 announcements is Cilium volunteering, the same MetalLB-style trick clouds
do with real load balancers. Compare the historical
`deploy/k8s/legacy/ingress-nginx.yaml` with `base/httproute.yaml`: Gateway API is the current
main path, while the old object remains only for migration analysis after ingress-nginx's
retirement.

## How it works (the one-paragraph mental model)

Cilium assigns every pod's labels a numeric **identity** and stamps it on traffic; eBPF
programs at the kernel's network hooks look up *identity × port* in per-node **BPF maps** to
enforce policy, and resolve Service VIPs with the same maps (often at `connect()` time) — that's
kube-proxy replaced. L7 rules can't be judged per-packet, so matching flows detour through a
node-local **Envoy** that answers 403s for denied requests. **Hubble** reads the datapath's
flow events and attaches identities. The **operator** implements Gateway API by turning
Gateway/HTTPRoute objects into Envoy config, **LB-IPAM** leases the Service an IP from a pool,
and **L2 announcements** make a node answer ARP for it. Every layer is still *desired state → a
controller → kernel state* — the reconcile pattern from lab 49, with a faster kernel half.

## Exercise — break the L7 rule, debug it with Hubble

The frontend's dashboard calls `GET /api/steps` through exactly the path you policed. Tighten
the policy until it breaks, then diagnose it the way you would in prod:

1. In `deploy/k8s/cilium/cnp-l7.yaml`, delete the `- method: "GET"` / `path: "/api/.*"` pair
   from `api-ingress-l7` (leave `/healthz` and `/readyz`), re-apply, and confirm the damage:
   `kubectl -n devops-dojo exec $fe -- wget -qO- -T3 http://api:8080/api/steps` → **403**.
2. Now pretend you didn't know that. Walk lab 49's decision tree — DNS resolves ✓, EndpointSlice
   populated ✓, pod Ready ✓ … yet requests fail. The tree needs a new branch: **policy**.
   `kubectl -n kube-system exec ds/cilium -- hubble observe --server ${relay}:80 --namespace devops-dojo --protocol http --last 10`
   — the DROPPED line names the verdict, the identities, and the exact method+path that was
   refused. That one line *is* the diagnosis.
3. Restore the rule, re-apply, confirm the GET returns 200, and note the general lesson: with
   L7 policy in play, "Service returns nothing" grows a fourth question — *does policy allow
   this request?* — and Hubble answers it in one command.

## Checkpoint

- ✅ You ran a working cluster with **no kube-proxy DaemonSet** and **zero KUBE-SVC iptables
  chains** — and Services behaved exactly as in lab 49.
- ✅ You read a ClusterIP's backends from the **eBPF maps** (`cilium-dbg service list` /
  `bpf lb list`) and watched them track a scale-up, replacing the `KUBE-SEP` chain count.
- ✅ You observed live flows with **Hubble** — L4, DNS and HTTP — with pod identities attached,
  in the CLI and the UI's service map.
- ✅ You proved the two flavors of deny: **403 from Envoy** (right identity, wrong method — L7)
  vs **timeout** (wrong identity — L3/4), and explained why lab 28 could only do the second.
- ✅ You ran the app's **Gateway + HTTPRoute** on Cilium and got a **real LoadBalancer IP** on
  kind via LB-IPAM + L2 announcements, and curl'd all three routes through it.

## Common failures

- `kubectl get gatewayclass` returns nothing → the Gateway API CRDs were applied **after**
  Cilium started (or not at all). Apply them, then
  `kubectl -n kube-system rollout restart deploy/cilium-operator` and re-check.
- `cilium-dbg: executable file not found` → older Cilium images call it `cilium` — swap the
  binary name (the flags are the same).
- Nodes `NotReady` right after `kind create cluster` → **expected** until the Cilium DaemonSet
  is up (there's no CNI before that). Only worry if they stay NotReady after the rollout.
- Cilium agents CrashLoop with API-server dial errors → the cluster isn't named `cilium`, so
  `k8sServiceHost: cilium-control-plane` in values.yaml points at nothing. Keep the names in
  kind-cilium.yaml and values.yaml in sync.
- Gateway `ADDRESS` assigned but curl hangs → your docker `kind` subnet doesn't contain the
  pool's CIDR (run the `docker network inspect` from step 5 and edit `lb-ipam-pool.yaml`), or
  the L2 policy's `interfaces` regex doesn't match the node NICs (`^eth[0-9]+` fits kind).
- Curl to the Gateway IP fails **from PowerShell** → by design on Docker Desktop: the host
  can't route to the kind bridge. Probe from a container on the `kind` network (step 5) — on a
  native-Linux host the IP would be directly reachable.
- `kubectl port-forward svc/cilium-gateway-dojo-gw` fails → that Service is **selectorless**
  (eBPF steers its traffic into Envoy; no pods back it), and port-forward needs a pod. Use the
  docker-network curl instead.
- `hubble observe` shows nothing for traffic you just sent → you queried a single agent's
  node-local buffer. Add `--server ${relay}:80` (step 3) to ask the relay for all nodes.
- `hubble observe --server hubble-relay.kube-system…:80` fails with `name resolver error:
  produced zero addresses` → the agent pod is **host-networked** and doesn't use cluster DNS.
  Pass the relay's **ClusterIP**, as step 3 does.
- The historical Ingress object is not applied → correct: no retired ingress-nginx controller
  is present. Both lab 22 and this cluster use Gateway API; their controllers/data planes differ.

## Where to go next

- **Lab 49, one more read**: you've now seen the *same* Service contract implemented twice —
  iptables DNAT chains there, eBPF maps here. That before/after is the strongest version of the
  "walk me through a packet" interview answer.
- **CKS territory**: `CiliumClusterwideNetworkPolicy`, host firewall, DNS-name egress
  allowlists (`toFQDNs`), TLS-aware inspection — the policy model you used scales to all of it.
- **Service mesh, revisited**: mTLS between all pods, traffic mirroring, ambient sidecars —
  [CURRICULUM.md](../../docs/CURRICULUM.md)'s out-of-scope note still stands, but you now hold
  the counter-argument from experience: identity-aware L7 policy + flow observability came from
  the CNI, no mesh required. Know what a mesh would still add (mTLS, cross-cluster) — that's
  the interview answer.

➡️ Back to the map: [docs/CURRICULUM.md](../../docs/CURRICULUM.md). The networking arc in one
line: lab 22 **used** it, lab 28 **secured** it, lab 49 **explained** it, lab 51 **swapped the
engine** — and nothing above the kernel noticed.

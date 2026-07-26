# Lab 53 — Scheduling: requests, taints, affinity, spread & preemption

**Maps to:** deepens labs 22/48 · **Milestone:** K8s deep-dive · **Cert:** CKA

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

> ℹ️ **Order note:** the folder number is out of sequence on purpose (appended later, like
> labs 48/49/51/52). This belongs in the **Kubernetes deep-dive** — scheduling is core CKA
> material the other labs only brushed (lab 48's control-plane taint, lab 49's Pending
> LoadBalancer). [CURRICULUM.md](../../docs/CURRICULUM.md) shows the intended order.

## Concept

Every pod you've created since lab 22 was placed by the **kube-scheduler**, and you've never
had to think about it — one more black box to open. Scheduling is a two-phase decision made
**once per pod**:

1. **Filter**: throw out nodes the pod *cannot* use — not enough unreserved **requests**
   (arithmetic, not live usage!), an untolerated **taint**, a failed **nodeSelector/affinity**
   match, a violated **anti-affinity/spread** rule.
2. **Score**: rank the survivors (preferred affinities, spread, images already present) and
   bind the pod to the winner. If **no node survives filtering**, the pod stays `Pending` with
   a `FailedScheduling` event that lists exactly which filter killed which node — the single
   most information-dense error message in Kubernetes, and the heart of every CKA scheduling
   task.

There's one escape hatch: a `Pending` pod with higher **priority** may **preempt** (evict)
lower-priority pods to make room. Everything in this lab is one of those filters, plus that
hatch.

## What you'll do

On lab 48's throwaway 3-node cluster: starve a pod on requests, steer with labels and
nodeSelector, repel with taints and re-admit with tolerations, contrast required-vs-preferred
affinity, cap replicas with hard anti-affinity vs balance them with spread constraints, then
fill a node and watch a high-priority pod evict its way in — finishing with a timed CKA-style
break-fix.

## Setup

The lab-48 cluster (1 control-plane + 2 workers, default CNI, no host ports — coexists with the
dojo cluster). Create or reuse it:

```powershell
kind create cluster --config deploy/k8s/kind/kind-cka.yaml
kubectl config use-context kind-cka
kubectl get nodes    # cka-control-plane, cka-worker, cka-worker2
```

One fact shapes everything below — the control-plane is **tainted**, so only the two workers
accept normal pods (the same taint lab 48 pointed at):

```powershell
kubectl describe node cka-control-plane | findstr Taints
#   node-role.kubernetes.io/control-plane:NoSchedule
```

All demo objects live in the `default` namespace.

## Steps

### 1. Requests are the scheduler's arithmetic

Read [impossible-request.yaml](../../deploy/k8s/scheduling/impossible-request.yaml): two
identical pods, one asks `cpu: "64"`, the other `100m`.

```powershell
kubectl apply -f deploy/k8s/scheduling/impossible-request.yaml
kubectl get pods greedy modest
#   greedy   Pending     modest   Running

kubectl describe pod greedy | findstr /i "FailedScheduling"
#   0/3 nodes are available: 1 node(s) had untolerated taint(s), 2 Insufficient cpu.
#   … preemption: 0/3 nodes are available: 3 Preemption is not helpful for scheduling.
```

Read that event the way the exam wants you to: **3 nodes, 3 reasons** — one filtered by taint
(the control-plane), two by CPU math. The tail also tells you preemption (step 7) can't rescue
it. And the math is over *requests*, checked against *allocatable*:

```powershell
kubectl get node cka-worker -o jsonpath="{.status.allocatable.cpu}"   # e.g. 20
kubectl describe node cka-worker | findstr /c:"Allocated resources" /c:"cpu  "
#   cpu  100m (0%)   <- barely anything reserved… yet 64 CPUs is still refused
```

*Aha:* the scheduler **bin-packs promises, never measurements**. A node "full" of requests can
sit idle, and an unrequested memory hog schedules fine (then gets OOM-killed — limits are the
runtime's job, requests the scheduler's). That's why lab 22's manifests all carry requests: no
requests = invisible to this arithmetic.

```powershell
kubectl delete pod greedy modest
```

### 2. nodeSelector — and why running pods never move

[nodeselector-pod.yaml](../../deploy/k8s/scheduling/nodeselector-pod.yaml) demands a node
labeled `disk=fast`. No node has it yet:

```powershell
kubectl apply -f deploy/k8s/scheduling/nodeselector-pod.yaml
kubectl get pod picky                              # Pending
kubectl describe pod picky | findstr /i "FailedScheduling"
#   0/3 nodes are available: 1 node(s) had untolerated taint(s),
#   2 node(s) didn't match Pod's node affinity/selector.

# Create the label and the scheduler retries Pending pods on its own:
kubectl label node cka-worker disk=fast
kubectl get pod picky -o wide                      # Running, NODE=cka-worker

# Now take the label away from under it:
kubectl label node cka-worker disk-
kubectl get pod picky -o wide                      # STILL Running on cka-worker
```

*Aha:* scheduling is a **one-shot admission decision**. Nothing re-evaluates placement for
running pods — remove the label, the pod stays; delete and re-create it, `Pending` again. Keep
this in mind whenever you "fix" labels/taints and nothing seems to happen: the fix applies to
the *next* scheduling, not the current placement. (The de-scheduler exists precisely because
of this gap.)

```powershell
kubectl delete pod picky
```

### 3. Taints repel, tolerations permit

Labels+selectors *pull* pods toward nodes; **taints** *push* them away — the direction reserved
for the node's owner. Dedicate a worker to a team:

```powershell
kubectl taint node cka-worker2 dedicated=payments:NoSchedule
kubectl apply -f deploy/k8s/scheduling/tolerations-deploy.yaml
kubectl get pods -l app=web -o wide
#   all 4 on cka-worker — cka-worker2 repels everything now
```

Open [tolerations-deploy.yaml](../../deploy/k8s/scheduling/tolerations-deploy.yaml), **uncomment
the tolerations block** (this lab's type-it moment), and re-apply:

```powershell
kubectl apply -f deploy/k8s/scheduling/tolerations-deploy.yaml
kubectl rollout status deploy/web
kubectl get pods -l app=web -o wide                # spread across BOTH workers again
```

Two subtleties the exam loves: **`NoSchedule` doesn't evict** — pods already on the node when
you taint it keep running (that's what `NoExecute` is for: it evicts, honoring
`tolerationSeconds`). And a toleration only made cka-worker2 *possible* again — it didn't
*send* pods there.

*Aha:* **taints keep everyone out; tolerations let someone in; nothing pulls them in.** Truly
dedicating a node takes the pair: a taint (exclude others) **plus** node affinity (attract
yours) — quote that pairing in an interview and you've answered the whole question. It's also
exactly how the control-plane stays app-free, as the Setup showed.

```powershell
kubectl delete deploy web
kubectl taint node cka-worker2 dedicated=payments:NoSchedule-     # untaint (note the minus)
```

### 4. Node affinity: required vs preferred

nodeSelector can only say "exactly this label". [node-affinity.yaml](../../deploy/k8s/scheduling/node-affinity.yaml)
shows its successor in both strengths — same `disk=fast` demand, different consequences (no
node has the label right now):

```powershell
kubectl apply -f deploy/k8s/scheduling/node-affinity.yaml
kubectl get pods require-fast prefer-fast -o wide
#   require-fast   Pending    <- hard requirement, no qualifying node
#   prefer-fast    Running    <- preference: scored, not filtered

# Satisfy the requirement and watch the Pending pod land:
kubectl label node cka-worker disk=fast
kubectl get pod require-fast -o wide               # Running on cka-worker
```

*Aha:* the strength is written into the field name —
`requiredDuringScheduling`**`IgnoredDuringExecution`**. Even the *hard* rule is only hard **at
scheduling time**: un-label the node and `require-fast` keeps running (step 2's lesson,
formalized in the API's own vocabulary). `preferred…` + `weight` is what you want in prod for
"nice-to-have" placement — `required` turns every label typo into an outage.

```powershell
kubectl delete pod require-fast prefer-fast
kubectl label node cka-worker disk-
```

### 5. Pod anti-affinity — HA that can bite

Spreading replicas across nodes is the standard HA move. [anti-affinity.yaml](../../deploy/k8s/scheduling/anti-affinity.yaml)
runs the same 3-replica deployment twice — hard and soft anti-affinity — on a cluster with
only **two** schedulable workers:

```powershell
kubectl apply -f deploy/k8s/scheduling/anti-affinity.yaml
kubectl get pods -l "app in (spread-hard,spread-soft)" -o wide
#   spread-hard: 2 Running (one per worker), 1 Pending — FOREVER
#   spread-soft: 3 Running — two share a node

kubectl describe pod -l app=spread-hard | findstr /i "FailedScheduling"
#   0/3 nodes are available: 1 node(s) had untolerated taint(s),
#   2 node(s) didn't match pod anti-affinity rules.
```

*Aha:* `required` anti-affinity **silently caps replicas at node count** — a real outage
pattern: a node dies, replicas can't reschedule onto the survivors *because a sibling is
already there*, and your "HA" config is now the reason you're degraded. Default to
`preferred` (or step 6's spread constraints); reserve `required` for genuine
never-co-locate constraints (licensing, noisy neighbors, compliance).

```powershell
kubectl delete deploy spread-hard spread-soft
```

### 6. topologySpreadConstraints — spreading, quantified

Anti-affinity is binary: co-locate never/avoid. [topology-spread.yaml](../../deploy/k8s/scheduling/topology-spread.yaml)
states the *actual* goal — balance — as arithmetic: across nodes, replica counts may differ by
at most `maxSkew: 1`. Six replicas, two usable workers, so 3/3. Run it:

```powershell
kubectl apply -f deploy/k8s/scheduling/topology-spread.yaml
kubectl get pods -l app=balanced -o wide
#   1 on cka-worker, 1 on cka-worker2 … and FOUR Pending. Not 3/3 at all.

kubectl describe pod -l app=balanced | findstr /i "FailedScheduling"
#   0/3 nodes are available: 1 node(s) had untolerated taint(s),
#   2 node(s) didn't match pod topology spread constraints.
```

Why? A **domain** is every node carrying the topology key — and that includes
`cka-control-plane`, which is tainted and can never run these pods. By default
(`nodeTaintsPolicy: Ignore`) the scheduler measures skew against that permanently-empty
domain: a third pod on a worker would mean skew `3 - 0 = 2`, over the limit, so it refuses.
Your "balanced" deployment is stuck at 2 replicas because of a node it was never going to use.

Uncomment `nodeTaintsPolicy: Honor` in the manifest — exclude nodes whose taints this pod
doesn't tolerate — and re-apply:

```powershell
kubectl apply -f deploy/k8s/scheduling/topology-spread.yaml
kubectl get pods -l app=balanced -o wide
#   3 on cka-worker, 3 on cka-worker2 — the enforced 3/3 split, at last
```

Same spec with `topologyKey: topology.kubernetes.io/zone` is how production survives an
availability-zone outage — the mechanism behind every "multi-AZ" checkbox.

*Aha:* spread constraints are what Deployments should usually use; anti-affinity is the
sledgehammer. But **`DoNotSchedule` counts domains you can't use** — an unschedulable,
tainted, or cordoned node silently caps your replica count until `nodeTaintsPolicy: Honor`
(or `whenUnsatisfiable: ScheduleAnyway`) tells the scheduler to stop counting it. That is the
single most common way topology spread "mysteriously" wedges a rollout.

```powershell
kubectl delete deploy balanced
```

### 7. PriorityClass & preemption — the queue jumper

With no PriorityClasses, every pod ties at priority 0 and `Pending` means *wait*. Read
[priorityclasses.yaml](../../deploy/k8s/scheduling/priorityclasses.yaml) (two classes: 1000 and
1000000) and [preemption-filler.yaml](../../deploy/k8s/scheduling/preemption-filler.yaml)
(40 × 1-CPU low-priority pods pinned to `cka-worker` — deliberately more than any laptop node
holds, so *some* stay Pending, proving the node is truly full):

```powershell
kubectl apply -f deploy/k8s/scheduling/priorityclasses.yaml
kubectl apply -f deploy/k8s/scheduling/preemption-filler.yaml
Start-Sleep 30
kubectl get pods -l app=filler --no-headers | Group-Object { ($_ -split "\s+")[2] } | Select-Object Name,Count
#   Running  19          <- however many CPUs the node has
#   Pending  21          <- the node is genuinely FULL. That's the point.
```

Now type the VIP yourself (save as `vip.yaml`, then apply — same node, same 1-CPU request,
higher class):

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: vip
spec:
  priorityClassName: dojo-high
  nodeSelector:
    kubernetes.io/hostname: cka-worker
  containers:
    - name: app
      image: nginx:1.27-alpine
      resources:
        requests:
          cpu: "1"
```

```powershell
kubectl apply -f vip.yaml
kubectl get pod vip -o wide                        # Running — on the FULL node
kubectl get events --field-selector reason=Preempted
#   Normal  Preempted  pod/filler-…  Preempted by pod <vip's UID> on node cka-worker
```

A filler died for this: the scheduler found no room, picked the lowest-priority victim whose
removal makes the VIP fit, evicted it (the deployment re-creates it — straight into the
Pending queue), and bound the VIP.

*Aha:* priority only exists once you define classes — and preemption **evicts, it doesn't
queue-jump politely**. That's the difference between "the batch job waits" and "the batch job
gets killed", and why prod clusters pair PriorityClasses with PodDisruptionBudgets (lab 48's
drain drill: PDBs are honored by drains — but preemption can override them if nothing else
fits).

```powershell
kubectl delete pod vip; kubectl delete deploy filler
kubectl delete pc dojo-low dojo-high; del vip.yaml
```

## How it works (the one-paragraph mental model)

For each unbound pod the scheduler **filters** nodes — allocatable minus requested resources
(`Insufficient cpu`), taints vs tolerations (`untolerated taint`), nodeSelector/affinity
(`didn't match … selector`), anti-affinity and spread (`didn't match pod anti-affinity rules`,
`didn't satisfy … topology spread`) — then **scores** survivors (preferred affinities, skew,
image locality) and binds once; nothing ever re-places a running pod. The `FailedScheduling`
event is the filter phase's full accounting — *n* nodes, *n* reasons — read it before touching
anything. If filtering leaves nothing and the pod's **priority** beats someone's, **preemption**
evicts the cheapest sufficient victims and retries. Requests are promises used for this math;
limits are enforced later, by the kubelet — two different systems that only meet in the YAML.

## Exercise — the 5-minute CKA drill

Set the stage (label + taint the same node):

```powershell
kubectl label node cka-worker2 disk=fast
kubectl taint node cka-worker2 dedicated=payments:NoSchedule
```

Type this pod as `fixme.yaml` and apply it. It can **never** schedule — it has **three**
compounding faults. Set a 5-minute timer and fix all three using nothing but
`kubectl describe pod fixme` events (the exam allows the docs; so do you):

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: fixme
spec:
  nodeSelector:
    disk: fastest
  tolerations:
    - key: dedicated
      operator: Equal
      value: payments
      effect: NoExecute
  containers:
    - name: app
      image: nginx:1.27-alpine
      resources:
        requests:
          cpu: "64"
```

<details>
<summary>Check yourself (after the timer)</summary>

1. `nodeSelector` says `fastest`, the label is `fast` — no node matches.
2. The toleration's `effect: NoExecute` does **not** tolerate a `NoSchedule` taint — effects
   must match. Fix to `NoSchedule`.
3. `cpu: "64"` — `Insufficient cpu` even on the right node. Drop to `100m`.

Pod specs are largely immutable: fix the YAML, `kubectl delete pod fixme`, re-apply. Done when
`fixme` runs **on cka-worker2**.
</details>

Clean up (or just `kind delete cluster --name cka`):

```powershell
kubectl delete pod fixme; del fixme.yaml
kubectl taint node cka-worker2 dedicated=payments:NoSchedule-
kubectl label node cka-worker2 disk-
```

## Checkpoint

- ✅ You read a `FailedScheduling` event as "*n* nodes, *n* reasons" and matched each reason to
  its filter (requests, taint, selector).
- ✅ You proved requests-vs-allocatable arithmetic decides placement — and that live usage
  plays no part.
- ✅ You showed scheduling is one-shot: label changes strand or free only *future* pods.
- ✅ You dedicated a node with a taint, re-admitted pods with a toleration, and can state why
  dedication needs taint **+** affinity.
- ✅ You contrasted required vs preferred (node affinity and pod anti-affinity), including how
  `required` anti-affinity caps replicas at node count.
- ✅ You enforced a 3/3 split with `maxSkew: 1` and can say when to reach for spread instead of
  anti-affinity.
- ✅ You watched a `dojo-high` pod preempt a `dojo-low` pod on a full node, and found the
  `Preempted` event.
- ✅ You fixed the three-fault pod inside 5 minutes, from events alone.

## Common failures

- "I fixed the label/taint and nothing happened" → the pod scheduled (or failed) **before**
  your fix; running pods never move, and Pending pods *do* get retried — know which case
  you're in (`kubectl get pod -o wide`).
- Forgot to untaint/unlabel between steps → later steps behave mysteriously; each step above
  ends with its cleanup — run it. (`kubectl describe node cka-worker2 | findstr Taints` when
  in doubt.)
- Taint removal syntax → it's the trailing **minus**: `kubectl taint node X key=value:Effect-`
  (same idea as `kubectl label node X key-`).
- Expected the control-plane to take pods → it's tainted by design on multi-node kind (lab 48);
  that's why every capacity count above says "2 usable workers", and why single-node kind
  (which drops the taint) behaves differently.
- `filler` pods all Running, none Pending (big desktop CPU) → preemption may not trigger;
  scale up: `kubectl scale deploy filler --replicas=80`.
- Preemption didn't kill anything → check the VIP actually *needs* the full node
  (`nodeSelector` pinned? request `"1"`?) and that `dojo-high` exists — a missing
  PriorityClass fails pod admission outright.

## Where to go next

- **[Lab 48 — CKA readiness](../48-cka-exam-readiness/)**: re-run the mock exam; scheduling
  tasks should now be your fastest section. Drain-vs-PDB there is this lab's preemption story
  from the ops side.
- **[Lab 21 — scaling](../21-scaling/) / [31 — KEDA](../31-k8s-keda-autoscaling/)**:
  autoscalers *create* pods; everything here decides *where they land* — capacity planning is
  these two systems multiplied.
- **[Lab 52 — storage](../52-k8s-storage/)**: `WaitForFirstConsumer` was the storage system
  deferring to this lab's decision — you've now seen both halves of that handshake.

➡️ Back to the map: [docs/CURRICULUM.md](../../docs/CURRICULUM.md). Lab 22 ran the pods,
lab 48 ran the cluster — **lab 53 explains who put every pod where it is.**

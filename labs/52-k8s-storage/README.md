# Lab 52 — Kubernetes storage: StorageClass, PV/PVC lifecycle, reclaim & access modes

**Maps to:** deepens labs 07/22 · **Milestone:** K8s deep-dive · **Cert:** CKA

**Run from:** the **repo root** (`learnDevops/`) — every command and path in this lab is relative to it, *not* to this lab folder.

> ℹ️ **Order note:** the folder number is out of sequence on purpose (appended later, like
> labs 48/49/51). This belongs in the **Kubernetes deep-dive** — Storage is a full CKA exam
> domain, and until now the repo has used exactly one PVC (Postgres, lab 22) without ever
> opening it up. [CURRICULUM.md](../../docs/CURRICULUM.md) shows the intended order.

## Concept

Since lab 22 the database has quietly ridden on a `volumeClaimTemplates` block — you asked for
1Gi and storage appeared. This lab opens that box. Kubernetes storage is a **matching game**
between three objects:

1. A **PersistentVolumeClaim (PVC)** is the *request*: "I need 100Mi, writable by one node."
2. A **PersistentVolume (PV)** is the *supply*: an actual chunk of storage, hand-written by an
   admin (**static** provisioning) or stamped out on demand by a provisioner (**dynamic**).
3. A **StorageClass** is the *vending machine*: which provisioner, what reclaim policy, and
   *when* to bind (`volumeBindingMode`). A cluster's **default** class is injected into any PVC
   that doesn't name one — which is how lab 22 worked without you ever choosing.

The lifecycle details — `WaitForFirstConsumer`, `Delete` vs `Retain`, `Released` vs
`Available`, access modes — are exactly what the CKA storage domain drills, and exactly what
bites in prod when someone deletes a PVC and asks "is the data gone?".

## What you'll do

On the lab-22 kind cluster: read the default StorageClass, provision dynamically and watch
*when* binding happens, flip the reclaim policy and rescue a `Released` volume, hand-write a
static PV, request an impossible access mode, hit the volume-expansion wall — then re-read the
Postgres StatefulSet's storage with new eyes.

## Setup

Steps 1–6 need only the lab-22 kind cluster; step 7 also wants the dojo stack running on it
(the [lab 49 Setup block](../49-k8s-networking-deep-dive/README.md#setup) stands it up). All
demo objects live in the `default` namespace, away from the app.

```powershell
kubectl config use-context kind-kind      # the lab-22 cluster
kubectl get nodes                         # single node: kind-control-plane
```

## Steps

### 1. Read the default StorageClass — the choice you never made

```powershell
kubectl get storageclass
#   NAME                 PROVISIONER             RECLAIMPOLICY   VOLUMEBINDINGMODE      ALLOWVOLUMEEXPANSION
#   standard (default)   rancher.io/local-path   Delete          WaitForFirstConsumer   false

kubectl describe sc standard | findstr /i "IsDefaultClass Provisioner ReclaimPolicy VolumeBindingMode"
```

Three facts to hold on to: **`(default)`** comes from the
`storageclass.kubernetes.io/is-default-class` annotation — an admission plugin stamps this
class into any PVC that omits `storageClassName`. The **provisioner** (`rancher.io/local-path`,
a pod in the `local-path-storage` namespace — kind ships it) creates volumes as plain
directories on the node. And **`WaitForFirstConsumer`** delays everything, as step 2 shows.

*Aha:* "default" is not a fallback inside the PVC — it's a **mutation at admission time**. The
Postgres claim in [postgres-statefulset.yaml](../../deploy/k8s/base/postgres-statefulset.yaml)
has no `storageClassName` in Git, but read it live and the field is filled in:
`kubectl -n devops-dojo get pvc data-db-0 -o jsonpath="{.spec.storageClassName}"` → `standard`.

### 2. Dynamic provisioning — and *when* binding actually happens

Apply the claim **alone** first ([pvc-dynamic.yaml](../../deploy/k8s/storage/pvc-dynamic.yaml)):

```powershell
kubectl apply -f deploy/k8s/storage/pvc-dynamic.yaml
kubectl get pvc demo-dynamic                      # STATUS: Pending — is that bad?
kubectl describe pvc demo-dynamic | findstr /i "waiting"
#   WaitForFirstConsumer  waiting for first consumer to be created before binding
```

Pending, and **healthy**. The class says `WaitForFirstConsumer`: don't create a volume until a
pod is scheduled, because only then is it known *which node* the data must live on. Give it its
consumer ([consumer-pod.yaml](../../deploy/k8s/storage/consumer-pod.yaml)):

```powershell
kubectl apply -f deploy/k8s/storage/consumer-pod.yaml
kubectl wait --for=condition=ready pod/writer --timeout=120s
kubectl get pvc demo-dynamic                      # Bound
kubectl get pv                                    # a pvc-… volume appeared, Delete policy

# The "volume" is a directory on the node. Find the actual bytes:
docker exec kind-control-plane ls /var/local-path-provisioner/
kubectl exec writer -- tail -2 /data/log          # the timestamps it's been writing
```

*Aha:* Pending-by-design vs Pending-broken is a state you must be able to tell apart under exam
pressure — `describe` and read the event. `waiting for first consumer` is the healthy one; step
5 and the Exercise show the broken kind.

### 3. Reclaim policy — where deleted data goes

The default class says `Delete`: the PV dies with its PVC.

```powershell
kubectl delete pod writer; kubectl delete pvc demo-dynamic
kubectl get pv                                    # …and the pvc-… volume is GONE
```

Now the same flow on a class that says **`Retain`**
([retain-storageclass.yaml](../../deploy/k8s/storage/retain-storageclass.yaml) — read it: same
provisioner, one field changed, plus its own claim and writer pod):

```powershell
kubectl apply -f deploy/k8s/storage/retain-storageclass.yaml
kubectl wait --for=condition=ready pod/writer-retain --timeout=120s
kubectl exec writer-retain -- tail -1 /data/log   # data is flowing

# The "oops": someone deletes the claim.
kubectl delete pod writer-retain; kubectl delete pvc demo-retain
kubectl get pv
#   STATUS: Released  (NOT Available, NOT gone)   RECLAIM POLICY: Retain

# Note the volume's name NOW, while exactly one PV is Released — you'll need it
# later, and by then there will be two:
$pv = kubectl get pv -o jsonpath="{.items[?(@.status.phase=='Released')].metadata.name}"
$pv
```

The bytes are still on the node (`docker exec kind-control-plane ls /var/local-path-provisioner/`).
Now the trap. Recreate the claim exactly as it was, and watch what you *don't* get back:

```powershell
kubectl apply -f deploy/k8s/storage/retain-storageclass.yaml   # PVC comes back, pod too
kubectl wait --for=condition=ready pod/writer-retain --timeout=120s
kubectl get pvc demo-retain                       # Bound — looks fine!
kubectl exec writer-retain -- head -1 /data/log   # …but the timestamps start from NOW
kubectl get pv                                    # TWO volumes: one Released (your data), one Bound (empty)
```

That is the failure mode worth remembering: the claim bound to a **brand-new empty volume**.
Nothing errored, nothing warned — the provisioner simply made another one, and your data is
stranded in the `Released` PV. It stays stranded because a Released PV still carries a
`claimRef` to the *deleted* claim (same name, different UID), so nobody is allowed to bind it.

Recovering it is a deliberate two-step — the CKA move. Clear the stale `claimRef`, then claim
that **exact** volume by name (`spec.volumeName`), or dynamic provisioning races ahead and hands
you yet another empty one:

```powershell
# Throw the empty volume away (this leaves a SECOND Released PV behind — which is
# exactly why you captured $pv earlier instead of querying for it now):
kubectl delete pod writer-retain; kubectl delete pvc demo-retain

# 1) clear the stale claimRef on YOUR volume -> the PV becomes Available.
#    NOTE the \" escaping: PowerShell mangles bare JSON on its way to kubectl.
kubectl patch pv $pv --type=json -p '[{\"op\":\"remove\",\"path\":\"/spec/claimRef\"}]'
kubectl get pv $pv                                # STATUS: Available

# 2) claim that volume BY NAME — read pvc-recover.yaml, then substitute the name:
(Get-Content deploy/k8s/storage/pvc-recover.yaml) -replace 'REPLACE_ME', $pv | kubectl apply -f -
kubectl wait --for=condition=ready pod/reader --timeout=120s
kubectl get pvc demo-recovered                    # Bound to the OLD volume
kubectl exec reader -- head -2 /data/log          # the ORIGINAL timestamps — data recovered
```

*Aha:* `Retain` turns "user deleted a PVC" into an ops ticket **on purpose** — but it does not
make recovery automatic, and it does not stop the app from cheerfully restarting on a fresh
empty disk. `Released` means "data preserved, admin decision required"; recovery is claimRef
surgery **plus** an explicit `volumeName`, and deletion is a second, deliberate
`kubectl delete pv`.

```powershell
# Clean up step 3. The PV is Retain, so it outlives its claim — delete it explicitly,
# and mop up any other Released volumes this step left behind:
kubectl delete pod reader; kubectl delete pvc demo-recovered
kubectl delete pv $pv
kubectl delete sc standard-retain
```

### 4. Static provisioning — what the robot automates

Dynamic provisioning is new(ish); the original model was an admin **hand-writing PVs** and users
claiming them. Read [pv-static.yaml](../../deploy/k8s/storage/pv-static.yaml) — a PV built from
a `hostPath`, and a claim that matches it:

```powershell
kubectl apply -f deploy/k8s/storage/pv-static.yaml
kubectl get pv static-pv
#   STATUS: Bound   CLAIM: default/static-pvc     <- bound with no provisioner involved
kubectl get pv static-pv -o jsonpath="{.spec.claimRef.name}"   # static-pvc — the controller wrote this
```

The binder matched on three things: `storageClassName` (`""` on **both** sides — an explicit
opt-*out* of the default class, not an omission), access mode (RWO ⊆ RWO), and size (the PV's
100Mi ≥ the claim's 50Mi — a PV may over-deliver, never under-deliver).

*Aha:* dynamic provisioning is just a robot writing this same PV object for you, on demand.
When you see bare-metal/NFS clusters with a wall of hand-made PVs, this is what you're looking
at — and `storageClassName: ""` is how their claims dodge the default class.

### 5. Access modes are capabilities, not locks

`ReadWriteOnce` means one **node** (not one pod!) can mount the volume read-write. Local-path
volumes are directories on a single node, so RWO is all the provisioner can promise. Ask it for
`ReadWriteMany` ([pvc-rwx.yaml](../../deploy/k8s/storage/pvc-rwx.yaml) — with a consumer,
because without one WaitForFirstConsumer would hide the real error behind "waiting for first
consumer"):

```powershell
kubectl apply -f deploy/k8s/storage/pvc-rwx.yaml
kubectl get pvc demo-rwx                           # Pending — and this time it's BROKEN-pending
kubectl describe pvc demo-rwx | findstr /i "failed"
#   Warning  ProvisioningFailed  …  failed to provision volume with StorageClass "standard":
#   NodePath only supports ReadWriteOnce and ReadWriteOncePod (1.22+) access modes
```

*Aha:* access modes are **matched capabilities** — a claim's mode must be a subset of what the
volume can do; nothing at runtime "locks" a RWO volume to one pod (two pods on the *same node*
can share it). RWX needs storage that's network-attached by nature: NFS, CephFS, EFS/Azure
Files — that's a CSI-driver decision, not a YAML flag.

```powershell
kubectl delete -f deploy/k8s/storage/pvc-rwx.yaml   # clean up the doomed pair
```

### 6. Expansion is a StorageClass privilege

```powershell
kubectl apply -f deploy/k8s/storage/pvc-dynamic.yaml; kubectl apply -f deploy/k8s/storage/consumer-pod.yaml
kubectl wait --for=condition=ready pod/writer --timeout=120s

# Ask for more space (again: \" escaping, or PowerShell mangles the JSON):
kubectl patch pvc demo-dynamic -p '{\"spec\":{\"resources\":{\"requests\":{\"storage\":\"200Mi\"}}}}'
#   Error from server (Forbidden): persistentvolumeclaims "demo-dynamic" is forbidden: only
#   dynamically provisioned pvc can be resized and the storageclass that provisions the pvc
#   must support resize
kubectl get sc standard -o jsonpath="{.allowVolumeExpansion}"   # (empty = false)
```

Growing a volume requires `allowVolumeExpansion: true` on the class **and** a CSI driver that
implements resize (local-path does neither). On EBS/AzureDisk classes this same patch triggers
a real cloud resize plus a filesystem grow.

*Aha:* **shrinking is never allowed** — the API rejects a smaller request outright. Growing is
opt-in per class. Remember the asymmetry; it's a one-line CKA question and a real capacity-
planning constraint.

```powershell
kubectl delete pod writer; kubectl delete pvc demo-dynamic      # clean up
```

### 7. The claim you've trusted since lab 22

Now re-read the Postgres StatefulSet's storage with all of the above loaded (needs the dojo
stack running):

```powershell
kubectl -n devops-dojo get pvc
#   data-db-0   Bound   … 1Gi   standard    <- volumeClaimTemplates stamped "data-<pod>"

# Kill the pod: the PVC (and data) survive — the StatefulSet re-attaches by NAME:
kubectl -n devops-dojo delete pod db-0
kubectl -n devops-dojo wait --for=condition=ready pod/db-0 --timeout=180s
kubectl -n devops-dojo get pvc data-db-0           # same PVC, untouched

# Scale the whole StatefulSet away — the PVC STILL survives:
kubectl -n devops-dojo scale sts db --replicas=0
kubectl -n devops-dojo get pvc data-db-0           # still Bound, still 1Gi
kubectl -n devops-dojo scale sts db --replicas=1
```

That survival is governed by the StatefulSet's `persistentVolumeClaimRetentionPolicy` — unset
means `Retain` for both "when deleted" and "when scaled" — a *second* retain layer on top of
step 3's PV-level reclaim policy.

*Aha:* StatefulSet PVCs outlive the pods **and** the StatefulSet itself. Losing data takes a
separate, deliberate `kubectl delete pvc` — and if someone does that anyway, the PV reclaim
policy is the last line of defense, and lab 07's backups are the one after that.

## How it works (the one-paragraph mental model)

A **PVC** states a need; a **PV** is supply; the **binder** marries them by class + access mode
+ size, writing `claimRef` on the PV. A **StorageClass** automates the supply side: its
provisioner stamps out PVs on demand, its `volumeBindingMode` decides *when* (immediately, or
`WaitForFirstConsumer` so the volume lands on the node the pod chose), its `reclaimPolicy`
decides what a PV does when its claim dies (`Delete` the data, or hold it `Released` until an
admin acts), and `allowVolumeExpansion` gates growth. The default class is injected into
class-less claims at admission. StatefulSets add `volumeClaimTemplates` (one PVC per replica,
by name) plus their own retention policy. Same shape as everything else in Kubernetes: desired
state (claim) → controller (binder/provisioner) → real state (a directory, a cloud disk).

## Exercise — two Pendings, two diagnoses

Both of these claims stick at `Pending`. Diagnose each **from events alone** (`kubectl
describe pvc …`), *then* fix:

1. Type this claim yourself (the type-it part) with a **misspelled class**:
   `storageClassName: standrad`, 100Mi, RWO, name it `oops-class`. Apply it — no pod needed —
   and `describe` it:
   `Warning ProvisioningFailed … storageclass.storage.k8s.io "standrad" not found`.
   Broken, and it says so within seconds. Fix = correct the class name (the field is
   **immutable**, so delete and re-create the claim rather than editing it).
2. Apply `deploy/k8s/storage/pvc-dynamic.yaml` **alone** and leave it. Identical `Pending`
   status, completely different meaning:
   `Normal WaitForFirstConsumer … waiting for first consumer to be created before binding` —
   nothing is wrong; the fix is a consumer pod, not a repair.

Note which is which without looking at the class name: **`Warning` vs `Normal`** is the tell.

Write the rule in your notes: **`Pending` on a PVC is a symptom, never a diagnosis — the event
tells you which of the two stories you're in.**

## Checkpoint

- ✅ You read the default StorageClass and proved the default is injected at admission
  (`data-db-0` carries `standard` despite Git saying nothing).
- ✅ You watched `WaitForFirstConsumer` hold a PVC Pending until a pod scheduled, then found the
  provisioned bytes on the node.
- ✅ You deleted a `Delete`-class claim (PV vanished) and a `Retain`-class claim (PV went
  `Released`), and rescued the Released PV by clearing its `claimRef` — old data intact.
- ✅ You hand-wrote a static PV and explained the three-way match (`""` class, mode, size).
- ✅ You proved local-path cannot do RWX (ProvisioningFailed) and cannot resize (forbidden),
  and can say which StorageClass fields would change that.
- ✅ You showed `data-db-0` survives pod deletion AND StatefulSet scale-to-zero.

## Common failures

- PVC `Pending` → **read the event before touching anything**: `waiting for first consumer` is
  healthy (make a pod), `not found` / `ProvisioningFailed` is broken (fix class/mode).
- Released PV won't re-bind → that's the design (stale `claimRef`); clear it with the step-3
  patch, or delete the PV if the data is expendable.
- `spec.storageClassName` edit rejected → most PVC spec fields are **immutable**; delete and
  re-create the claim (only the storage request can grow, and only when expansion is allowed).
- `kubectl patch` fails with `invalid character 's' looking for beginning of object key string`
  or `the server rejected our request` → PowerShell ate the JSON quotes. Escape them
  (`-p '{\"spec\":…}'`) as every patch command in this lab does; bare `-p='{"spec":…}'` works
  in bash but **not** in PowerShell.
- Deleted the PVC but disk usage didn't drop (Retain class) → the PV is holding the directory;
  reclaim = delete the PV *and* (local-path) the node directory.
- Everything vanished after `kind delete cluster` → hostPath/local-path data lives inside the
  node **container** — one more reason lab 07's `pg_dump` backups exist.

## Where to go next

- **[Lab 33 — Velero](../33-k8s-velero-backup/)**: now that you know what a PV *is*, Velero's
  volume snapshots and restores read very differently.
- **CSI drivers**: everything here spoke to `rancher.io/local-path`; on EKS the same YAML hits
  `ebs.csi.aws.com` (lab 25/40) — swap the class, keep the claims: that's the portability
  argument StorageClasses exist to make.
- **[Lab 53 — Scheduling](../53-k8s-scheduling/)**: `WaitForFirstConsumer` was storage waiting
  for the *scheduler* — next, meet the scheduler itself.

➡️ Back to the map: [docs/CURRICULUM.md](../../docs/CURRICULUM.md). Lab 22 asked for storage,
lab 07 backed it up — **lab 52 explains who granted it, and on what terms.**

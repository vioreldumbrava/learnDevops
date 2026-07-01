# Lab 33 — Backup & disaster recovery with Velero

**Maps to:** deepens §8 · **Milestone:** K8s deep-dive · **SRE**

## Concept

Lab 07 backed up the *database*. In Kubernetes you also need to back up **cluster state** — the
objects (Deployments, Services, ConfigMaps, PVCs) *and* the persistent volume data — so you can
restore a namespace, or the whole cluster, after a disaster or a bad change. **Velero** does
exactly that: scheduled backups to object storage, plus restore.

## What you'll do

Install Velero (with a local MinIO object store), schedule a namespace backup, then simulate a
disaster and restore.

## Steps

```powershell
# Local object store for kind (MinIO) — on EKS you'd point Velero at S3 instead.
# (helm install minio ...) then install the Velero CLI + server configured for it, e.g.:
velero install --provider aws --bucket velero --use-node-agent `
  --secret-file .\minio-credentials --backup-location-config `
  region=minio,s3ForcePathStyle=true,s3Url=http://minio.velero.svc:9000

kubectl apply -f deploy/k8s/backup/velero-schedule.yaml

# Take an on-demand backup now (don't wait for 03:00):
velero backup create dojo-now --include-namespaces devops-dojo --wait
velero backup describe dojo-now
```

Disaster + restore:

```powershell
kubectl delete namespace devops-dojo           # simulate loss
velero restore create --from-backup dojo-now --wait
kubectl -n devops-dojo get pods,pvc            # namespace and data are back
```

## How it works

[velero-schedule.yaml](../../deploy/k8s/backup/velero-schedule.yaml) is a `Schedule` that backs
up the `devops-dojo` namespace daily and retains backups for 7 days (`ttl: 168h`). Velero exports
the API objects to object storage and (with the node agent / CSI snapshots) captures PVC data.
Restore recreates the objects and volumes. The lesson mirrors lab 07: **a backup you've never
restored isn't a backup** — so we actually delete and restore.

## Exercise

Restore into a *different* namespace with `--namespace-mappings devops-dojo:dojo-restored` — the
standard way to validate a backup without touching production, and how you'd clone an environment.

## Checkpoint

- ✅ `velero backup describe dojo-now` shows `Phase: Completed`.
- ✅ After deleting the namespace, `velero restore` brings back pods and PVCs.
- ✅ You can explain why DB dumps (lab 07) and cluster backups (Velero) are complementary.

## Common failures

- Backup `PartiallyFailed` → the object store isn't reachable/credentials wrong; check
  `velero backup logs`.
- PVC data not restored → volume snapshots/node-agent not enabled; objects restore but empty
  volumes. Enable `--use-node-agent` or CSI snapshots.

➡️ Next: [Lab 34 — kube-prometheus-stack](../34-k8s-kube-prometheus-stack/)

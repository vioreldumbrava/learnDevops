# Lab 34 — Cluster monitoring with kube-prometheus-stack

**Maps to:** deepens §10 · **Milestone:** K8s deep-dive

## Concept

In Compose you ran Prometheus + Grafana yourself (lab 10). On Kubernetes the standard is the
**Prometheus Operator** (bundled in the **kube-prometheus-stack** Helm chart): it installs
Prometheus, Alertmanager, Grafana, and node/cluster exporters, and lets you declare scrape
targets as **`ServiceMonitor`** custom resources instead of editing `prometheus.yml`. You get
full cluster + node + control-plane metrics *and* your app metrics, managed declaratively.

## What you'll do

Install the stack and wire your API's `/metrics` into it with a ServiceMonitor.

## Steps

```powershell
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install kps prometheus-community/kube-prometheus-stack -n monitoring --create-namespace
kubectl -n monitoring rollout status deploy/kps-grafana --timeout=240s

# Make the api Service scrape-able (named port + label), then register it:
kubectl -n devops-dojo label service api app=api --overwrite
kubectl -n devops-dojo patch service api --type=json -p='[{\"op\":\"replace\",\"path\":\"/spec/ports/0/name\",\"value\":\"http\"}]'
kubectl apply -f deploy/k8s/observability/servicemonitor.yaml

# Open Prometheus + Grafana
kubectl -n monitoring port-forward svc/kps-kube-prometheus-stack-prometheus 9090:9090
kubectl -n monitoring port-forward svc/kps-grafana 3001:80   # admin / prom-operator
```

In Prometheus (Status ▸ Targets) the `dojo-api` ServiceMonitor target should be **UP**; query
`rate(dojo_http_requests_total[1m])`. Grafana ships with cluster/node dashboards out of the box.

## How it works

The operator watches for `ServiceMonitor` resources whose labels match its
`serviceMonitorSelector` (here `release: kps`) and auto-generates Prometheus scrape config.
[servicemonitor.yaml](../../deploy/k8s/observability/servicemonitor.yaml) selects the `api`
Service by its `app: api` label and scrapes its named `http` port at `/metrics` — the same
application metrics from lab 10, now discovered declaratively and sitting alongside kube-state
and node metrics.

## Exercise

Add a `PrometheusRule` (the operator's CRD form of the alert rules from lab 12) for
`HighErrorRate` on `dojo_http_requests_total{status=~"5.."}`, and confirm it appears in the
bundled Alertmanager. Now your alerting is declarative and version-controlled too.

## Checkpoint

- ✅ kube-prometheus-stack pods are running in `monitoring`.
- ✅ The `dojo-api` ServiceMonitor target is **UP** in Prometheus.
- ✅ Grafana shows both cluster/node dashboards and your app metrics.

## Common failures

- Target missing → the ServiceMonitor's `release:` label doesn't match the operator's selector
  (check `helm get values kps`), or the Service port isn't named `http`.
- Grafana login → default is `admin` / `prom-operator` for this chart.

🎉 You've now covered the Kubernetes depth that CKA/CKS and Platform/SRE interviews probe. See
[docs/CURRICULUM.md](../../docs/CURRICULUM.md) and [docs/INTERVIEW_PREP.md](../../docs/INTERVIEW_PREP.md).

# Interview Prep — turning DevOps Dojo into offers

This project is only worth as much as your ability to **explain and defend it**. Interviewers
don't grade the repo; they grade whether you understand *why* each piece exists and can debug
it under pressure. Use this doc to rehearse until every answer is second nature.

Golden rule: **for every tool in this project, be able to say what it does, why you chose it,
what the alternative was, and what you'd change for production.**

---

## 1. How to present it

- **Make it public.** Push to GitHub; pin the repo. A private repo doesn't exist to a recruiter.
- **Deploy it live.** Use the capstone (lab 25) or at least the EC2 path (labs 16–18) so you
  can share a URL. "Here, click it" beats any slide.
- **Lead with the architecture.** The diagram in [DOCKER_LEARNING_PATH.md](DOCKER_LEARNING_PATH.md)
  is your one-slide story.
- **Have the repo open** in the interview to screen-share `ci.yml`, the `Jenkinsfile`, the Helm
  chart, and the ArgoCD `Application` when asked.

### The 60-second pitch (memorize this)

> "DevOps Dojo is a 3-tier app — a Go API, a React frontend, Postgres and Redis — that I use
> to practice the full delivery lifecycle. Code is containerized with multi-stage, distroless,
> non-root images; run locally with Docker Compose overlays for dev/prod/observability. CI in
> GitHub Actions builds, tests, scans with Trivy, and pushes versioned images with an SBOM to
> GHCR — and I also wired the same pipeline in Jenkins to compare managed vs self-hosted.
> Infrastructure is Terraform, configured with Ansible. It's fully observable — Prometheus
> metrics, Loki logs, Tempo traces, Alertmanager. The capstone runs it on EKS, delivered by
> ArgoCD GitOps that self-heals and rolls back via Git."

---

## 2. Talk track — Q&A by topic

For each: a likely question, a strong answer grounded in the project, and the follow-up they'll
probably ask next.

### Containers & images

**Q: Walk me through your Dockerfile.**
> Multi-stage: a `golang` stage compiles a static binary (`CGO_ENABLED=0`), then I copy just
> that binary into `distroless/static:nonroot`. So the final image is a few tens of MB, has no
> shell or package manager, and runs as non-root — small attack surface and fast pulls. I order
> `COPY go.mod` + `go mod download` before the source so dependency layers stay cached.

**Follow-up — Q: Why distroless over alpine?** No shell/pkg manager means far less for an
attacker to use, and no libc surprises since the binary is static. Downside: harder to debug
(no `exec sh`), which is why the container healthcheck is the binary itself (`/api -healthcheck`).

### Docker Compose vs Kubernetes

**Q: When would you use Compose vs Kubernetes?**
> Compose for local dev and single-host setups — it's simple and fast. Kubernetes when I need
> multiple hosts, self-healing, rolling updates, and autoscaling. In my project the mapping is
> explicit: a Compose service becomes a Deployment+Service, a named volume becomes a PVC (a
> StatefulSet for Postgres), env becomes ConfigMap+Secret, the one-shot migrate becomes a Job,
> and Caddy becomes a Gateway plus HTTPRoute.

### Liveness vs readiness (a favorite)

**Q: What's the difference between a liveness and a readiness probe?**
> Liveness answers "is the process alive?" — if it fails, Kubernetes restarts the pod.
> Readiness answers "can it serve traffic right now?" — if it fails, it's pulled from the
> Service endpoints but *not* restarted. My API exposes both: `/healthz` is unconditional
> liveness; `/readyz` pings Postgres and Redis. Getting this wrong causes restart loops — e.g.
> restarting the app because the database is briefly slow.

### CI/CD (managed vs self-hosted)

**Q: Describe your CI/CD pipeline.**
> On every push, GitHub Actions runs `go vet`/`go test`, builds the frontend, validates
> Compose, and Trivy-scans dependencies. Then it builds both images with Buildx, tags them by
> branch/semver/SHA, attaches an SBOM and provenance, pushes to GHCR on non-PR events, and
> scans the pushed image by digest. PRs build and scan but don't push. I also implemented the
> same pipeline in Jenkins (`Jenkinsfile`) to understand self-hosted CI — agents, credentials,
> Docker-outside-of-Docker.

**Follow-up — Q: Actions or Jenkins?** Actions for GitHub-hosted repos with no infra to run;
Jenkins when you need on-prem/air-gapped control or its plugin ecosystem — but then you own
patching, scaling, and securing it.

### Infrastructure as Code & config management

**Q: Terraform and Ansible — why both?**
> Different jobs. Terraform is *provisioning* — it declares what infrastructure exists (VPC,
> EKS/EC2, security groups) and tracks it in state. Ansible is *configuration management* —
> it makes the server's software match a desired state idempotently (install Docker, render
> `.env`, run compose). Terraform = what exists; Ansible = how it's configured.

**Follow-up — Q: What's Terraform state and why care?** It's Terraform's record of real
resources — it can contain secrets (my generated SSH key does). I run the real setup: state
in **S3 with locking** (native lockfile; S3 + DynamoDB is the classic answer), one key per
root module, a reusable module consumed by directory-per-env roots, and
fmt/validate/tflint/checkov in CI (lab 39). I've watched the lock reject a concurrent plan —
that's the "why care".

### GitOps (the senior signal)

**Q: What is GitOps and why is it better than `kubectl apply` in CI?**
> GitOps makes Git the single source of truth and puts a controller (ArgoCD) *in* the cluster
> that continuously reconciles actual state to the repo. Benefits over push-based CI deploys:
> the cluster self-heals drift, every change is an auditable Git commit, rollback is
> `git revert`, and CI never needs cluster credentials. In my capstone, ArgoCD watches the
> Helm chart path and syncs with prune + self-heal.

**Follow-up — Q: How does a change reach production?**
> One chart, three values files, an ArgoCD **ApplicationSet** stamping out dev/staging/prod.
> Dev tracks the latest build and auto-syncs; promotion is a PR bumping the pinned image tag
> in `values-staging.yaml`, then `values-prod.yaml`; prod is manual-sync on purpose.
> `git log values-prod.yaml` *is* the deploy history (lab 36).

### Kubernetes internals — the operator you wrote

**Q: What actually happens when you `kubectl apply` a Deployment?** *(or: how do
controllers work?)*
> The API server validates it against the schema and stores it in etcd — nothing runs yet.
> Controllers *watch* the types they own and **reconcile**: read desired state (spec), read
> actual state, converge, write what they observed to **status**. It's level-based, not
> event-based — one code path handles create, update, tampering and restarts. I know this
> because I **wrote an operator** ([dojo-operator](../dojo-operator/)): a `DojoBackup` CRD
> whose controller manages scheduled Postgres backups — delete its CronJob and it resurrects,
> exactly like ArgoCD self-heals my deployments, because it's the same mechanism.

**Follow-up — Q: Why do namespaces get stuck in Terminating?**
> A **finalizer** whose controller never removed it. Finalizers are pre-delete hooks: the API
> server sets `deletionTimestamp` and holds the object until every finalizer is cleared. Mine
> blocks deletion while a backup Job is running. The fix is to give the controller what it's
> waiting for — force-clearing `metadata.finalizers` skips the cleanup and is a last resort
> for controllers that no longer exist. I've manufactured and fixed this failure on purpose
> (operator lab 04).

**Follow-up — Q: How do you secure something like that?**
> The operator runs as a ServiceAccount with a ClusterRole derived line-by-line from what the
> reconciler calls — and the sharpest line is what's *missing*: it has **no access to
> secrets**, because it only wires a `secretKeyRef` into the backup pod; the kubelet resolves
> the value. Add an API call without adding the verb and the operator breaks with `Forbidden`
> — RBAC doubles as a scope-creep tripwire.

**Q: Walk a packet from a Service ClusterIP to a pod. What is a ClusterIP, really?**
> It's a **virtual IP that no host owns** — ping it and nothing answers, but TCP works, because
> **kube-proxy** programmed the node's kernel (iptables DNAT rules, or IPVS) to rewrite packets
> aimed at the ClusterIP toward a real pod IP, load-balancing across the current endpoints. The
> **endpoint controller** keeps an **EndpointSlice** in sync with *ready* pods (failing
> readiness pulls a pod out, so it stops receiving traffic), and kube-proxy keeps the kernel in
> sync with the slice. **CoreDNS** resolves the Service name to that ClusterIP. So: DNS → VIP →
> kernel DNAT → pod. I've read those exact iptables chains off a kind node
> ([lab 49](../labs/49-k8s-networking-deep-dive/)). Modern CNIs (Cilium — GKE Dataplane V2,
> Azure CNI) replace those chains with **eBPF**: I've also run the same cluster kube-proxy-free
> and read the service map from the BPF side with `cilium-dbg` and Hubble
> ([lab 51](../labs/51-k8s-cilium-ebpf/)).

**Follow-up — Q: "A Service isn't responding" — how do you debug it?** *(the classic)*
> Isolate one layer at a time: **DNS** (does the name resolve? `nslookup`) → **Endpoints**
> (`kubectl get endpointslices` — *empty* means no ready pods, the most common cause) →
> **pod readiness** (`get pods`, `describe` the probe) → **kube-proxy** (rules present on the
> node?). Nine times in ten it's an empty EndpointSlice because a readiness probe is failing —
> the network is fine, the Service just has nothing to route to.

### Polyglot — Go vs Python, and fleet consistency

**Q: Go or Python for a backend service — how do you decide, and how do you keep a mixed fleet
sane?**
> I've built the *same* Dojo API twice — Go ([app/api](../app/api/)) and Python/FastAPI
> ([app/api-py](../app/api-py/)) — behind one contract, so I can speak to this concretely.
> **Go** when I want small images and high throughput: the static binary is a ~52 MB distroless
> image, instant start, a goroutine per request. **Python** when iteration speed or the data/ML
> ecosystem matters: FastAPI is ~550 lines vs ~690, at the cost of a ~276 MB image and an event
> loop instead of threads. The decider is the workload, not taste.
> **Consistency across a polyglot fleet** doesn't come from one language — it comes from shared
> **contracts**: both twins expose identical HTTP/JSON, the same `dojo_http_*` metric names, and
> the same structured-log shape, so one Prometheus/Grafana/Loki stack and one frontend serve
> either. I can hot-swap the backend language with a one-line Compose overlay (or
> `kubectl set image`) and nothing downstream notices — that's the proof the contract, not the
> code, is the interface (lab 50).

### Observability — the three pillars

**Q: How would you debug a slow endpoint in production?**
> Metrics first (Prometheus/Grafana) to see *what and how often* — request rate, error rate,
> p95 latency from my `/metrics`. Logs next (Loki) to see *what happened* — I query
> `{compose_service="api"} | json | status>=400`. Traces (Tempo) to see *where the time went* —
> my traces show a `store.*` DB span nested in the request span, so I can tell app vs DB time.
> Alertmanager pages me before users notice via rules like error-rate and p95 thresholds.

**Follow-up — Q: What SLO would you set for this service? What's an error budget?**
> The **SLI** is the measurement, the **SLO** is the target on it. Mine is *99.5% of requests
> succeed and complete under 500ms, over 30 days*, and it's **implemented, not hypothetical**
> ([lab 56](../labs/56-slo-and-error-budgets/)): recording rules over
> `dojo_http_requests_total` and the `dojo_http_request_duration_seconds` histogram — I read
> the latency SLI straight off the `le="0.5"` bucket rather than `histogram_quantile`, so
> there's no interpolation in the number I'm alerting on. The **error budget** is the allowed
> 0.5% ≈ 3h36m per 30 days: while budget remains you ship freely; when it's spent, feature
> releases pause. I wrote that down as an
> [error-budget policy](runbooks/error-budget-policy.md), because an SLO with no policy is
> just a dashboard.

**Follow-up — Q: So how do you alert on it?** *(the SRE question)*
> **Multi-window, multi-burn-rate** — I deleted my static "5xx > 5% for 5 minutes" rule to do
> it. Burn rate is how many times faster than sustainable you're spending the budget: at
> **14.4×** the whole 30-day budget is gone in two days, so that pages; **6×** pages;
> **1×** opens a ticket. Each alert pairs a **long** window ("is this real?") with a **short**
> one ("is it still happening?") — without the short one, a 6h window keeps firing for hours
> after you've fixed it and people learn to ignore it. Alertmanager routes `severity=page` vs
> `severity=ticket` and inhibits slow-burn when fast-burn is already firing.
> The trade-off I'd name unprompted: **burn-rate alerting needs traffic.** At three requests a
> minute one error is a 33% error rate, so for a low-traffic internal service a static
> threshold is still the honest choice. I've watched mine fire — kill the database, generate
> load, and fast-burn goes Firing in ~5 minutes while slow-burn stays Inactive.

### Security

**Q: How did you harden this?**
> Defense in depth: distroless non-root images; a hardening overlay adds `no-new-privileges`,
> `cap_drop: ALL`, and read-only root filesystems with tmpfs for scratch paths; database ports
> bind to `127.0.0.1` so only the reverse proxy is public; images are scanned with Trivy in CI
> and locally; TLS is automatic via Caddy/Let's Encrypt. I keep `.env` out of Git and know the
> next step is a real secrets manager (Vault / sealed-secrets / cloud secret store).

**Follow-up — Q: How do you know the image running in the cluster is the one CI built?**
> It's signed: CI signs the image **digest** with cosign keyless — the signing identity is
> the workflow's OIDC token, logged in the Rekor transparency log — and Kyverno verifies the
> signature at admission, so unsigned images from my registry don't run. CI also gates on
> CRITICAL vulnerabilities, with exceptions only via a justified `.trivyignore` (lab 41).

**Follow-up — Q: What's still not production-grade?** Honest answer: the demo password
defaults, plain-text secrets in `.env`/values for learning, and the single NAT gateway (no
HA) — I'd address those before real traffic. Network policies *used* to be on this list;
lab 28 closed it with default-deny + explicit allows on Calico — say so, it shows progress.

### Scaling — stateless vs stateful

**Q: How do you scale this, and what can't you scale?**
> The stateless services — api, worker, frontend — scale horizontally: more replicas behind a
> load balancer (Caddy with dynamic upstreams, or a K8s Service/HPA). The worker scales
> trivially because it just pulls from a Redis queue. Stateful services — Postgres, Redis —
> can't be scaled by adding copies; they need replication/clustering. Also, a service with a
> fixed host port can't have multiple replicas, so I drop the host port and front it with the
> proxy.

### Data: migrations & backups

**Q: How do schema changes and backups work?**
> Schema changes are versioned migrations (golang-migrate) run as a one-shot Job/Compose
> service; re-running is idempotent, so the app can depend on it every boot. Backups use
> `pg_dump` to a location *outside* the DB container, and I actually test restores — delete a
> row, restore, confirm it's back — because a backup you've never restored isn't a backup.

**Follow-up — Q: "The database is slow." Walk me through it.** *(the most common real incident)*
> Four steps, in this order. **Which query** — `pg_stat_statements` ranked by *total* time, not
> mean: a 2 ms query run 500,000 times beats a 400 ms query run twice. **Why** —
> `EXPLAIN (ANALYZE, BUFFERS)`, and I read *actual vs estimated rows* (an order-of-magnitude
> gap means stale stats, so `ANALYZE`) and *shared hit vs read* (cache vs disk). I ignore
> `cost` — it's a unitless planner estimate, not milliseconds. **Fix** — usually an index, and
> it ships as a **migration**, not a hand-typed `CREATE INDEX`, or it only exists on the box
> where the incident happened. **Prove** — same `EXPLAIN`, plus the p95 panel in Grafana
> before and after. I've done exactly this on my own stack ([lab 55](../labs/55-postgres-operations/)).

**Follow-up — Q: And if it isn't the query?**
> Then it's one of three, and they look nothing alike. **Locks** — `pg_blocking_pids()` names
> the blocker; the usual culprit is `idle in transaction`, a session holding locks while
> running nothing, which is why `pg_cancel_backend` does nothing to it and why
> `idle_in_transaction_session_timeout` exists. **Connections** — a Postgres connection is a
> whole backend *process*, so the ceiling is low; the answer is a pooler (PgBouncer, transaction
> mode) rather than raising `max_connections`, and the cost is that session state and
> server-side prepared statements stop working. **Bloat** — dead tuples from churn; `VACUUM`
> makes space reusable but doesn't shrink the file, and only `VACUUM FULL` returns disk to the
> OS, at the price of an `ACCESS EXCLUSIVE` lock you can't take on a busy table.

### Ecosystem breadth (labs 43–47)

**Q: Fifty Jenkinsfiles all build, scan and push the same way — how do you keep that sane?**
> A **Jenkins Shared Library**: the common steps live once in a versioned Groovy library
> (`vars/` = named steps) that every Jenkinsfile loads with `@Library`. Change the scan
> policy once, every pipeline gets it — the cost is a shared dependency that can break fifty
> pipelines at once, so it's versioned and pinned like any dependency. I also do dynamic
> versioning there: the pipeline bumps a VERSION file, tags images with it, and commits back
> with a `[ci skip]` marker — Jenkins has no built-in skip-ci, so without your own guard the
> bump commit re-triggers the pipeline forever (lab 43).

**Q: How does Ansible target servers that come and go?**
> **Dynamic inventory**: instead of IPs in a file, the AWS inventory plugin asks the cloud
> API at runtime — "give me running instances with this tag" — and groups them by tag. The
> tags Terraform writes are the contract Ansible selects on (lab 44). And on wiring the two:
> my `terraform apply` can trigger the playbook via a `local-exec` provisioner, but
> provisioners are a **last resort** — outside plan/state, no drift detection — so in CI I'd
> run provision and configure as two pipeline steps.

**Q: Helmfile vs ArgoCD — you have both. Why?**
> Same question, two delivery models. Helmfile declares releases as data and **pushes** from
> wherever it runs — simple, no controller in the cluster, ideal for CI-driven shops and
> local work; but nothing reconciles drift between runs. ArgoCD **pulls** from inside the
> cluster and continuously reconciles Git → cluster. For production fleets I'd choose GitOps
> (self-heal, audit, `git revert` = rollback); Helmfile when a controller is overkill
> (labs 36/46). Under both sits one chart with a **library chart** so thirty services share
> one Deployment shape instead of thirty copies.

**Q: We're an Azure shop and you learned on AWS — is that a problem?**
> No — and I tested that claim instead of asserting it: I deployed my exact Helm chart to
> **AKS** with zero template changes; only cluster creation and auth differed (lab 47).
> Kubernetes is the portability layer — kubectl, Helm, probes, RBAC, NetworkPolicies all
> transfer. What I'd map on day one: IAM → Entra + RBAC scopes, S3 → Blob, RDS → Azure
> Database, IRSA → Workload Identity, and resource groups make teardown *easier*. Deep on
> one cloud, conversational in the mapping ([CLOUD_PROVIDER_MAP.md](CLOUD_PROVIDER_MAP.md)).

---

## 3. Troubleshooting scenarios (think out loud, structured)

**"A pod is stuck in `CrashLoopBackOff`. What do you do?"**
1. `kubectl describe pod` — events (image pull? OOMKilled? failed mount?).
2. `kubectl logs` (and `--previous`) for the app error.
3. Check config: env/ConfigMap/Secret correct? Dependency (DB) reachable?
4. Reproduce locally with the same image if needed.
State the *method*, not a guess — that's what they're testing.

**"The site is up but returns 502."** Work the path: client → LB/Gateway/HTTPRoute → Service →
Pod/readiness. Is the Gateway controller/data plane healthy? Do Service endpoints exist (readiness
passing)? Can the pod serve directly (`kubectl port-forward`)?

**"Deploys are slow / images huge."** Multi-stage builds, smaller base (distroless/alpine),
layer caching order, `.dockerignore`, and build cache in CI (`cache-from/to: gha`).

**"How do you roll back a bad deploy?"** GitOps: `git revert` and ArgoCD syncs the previous
state (or ArgoCD History → Rollback). Without GitOps: redeploy the previous image tag /
`helm rollback` / `kubectl rollout undo`.

> 🥋 Don't just memorize these — **drill them**. Lab 35 injects each failure into your own
> cluster (`scripts/chaos/roulette.sh` picks one blind), the [runbooks](runbooks/) capture
> the diagnosis paths, and a written [postmortem](postmortem-template.md) turns a drill into
> a STAR story you can tell with real timestamps.

---

## 4. Behavioral: "Tell me about a project"

Use a light STAR:
- **Situation:** "I wanted to learn DevOps properly, so I built one real app and took it
  through the entire lifecycle instead of isolated tutorials."
- **Task:** "Containerize it, make it observable and secure, and deploy it to Kubernetes with a
  automated, auditable pipeline."
- **Action:** the 60-second pitch above.
- **Result:** "I can take a commit to a self-healing EKS deployment via GitOps, and I
  understand the trade-offs at each layer — which I documented as hands-on labs I drill 
  from scratch on a clock, not just notes I wrote once."

---

## 5. Weaknesses — name them before they do

Interviewers respect honesty over bluffing:

- "My production experience is from this project, not yet a high-traffic system on-call —
  but I've drilled incident response deliberately: eight break-fix scenarios on my own
  cluster, with runbooks and written postmortems (lab 35), and I run a blind one weekly."
- "I've run Kubernetes on kind and EKS, but haven't operated a large multi-team cluster."
- "My SLO is on a service with my traffic levels, not a million requests a minute — I know
  burn-rate alerting needs volume to be meaningful and I can say where it stops working."
- "Local/dev uses a demo password for convenience — but the chart supports `secrets.create=false`
  so real deployments get `dojo-secrets` from **Sealed Secrets** or the **External Secrets
  Operator** (lab 26), keeping plaintext out of Git." *(A gap I already closed — turn it into a
  strength.)*

Two that *used* to be on this list, worth naming as closed rather than hiding: NetworkPolicies
(lab 28 — default-deny with explicit allows) and "I can describe SLOs but haven't built one"
(lab 56 — recording rules, multi-window burn-rate alerts, and a written error-budget policy).
Saying "that was a gap; here's what I did about it" is stronger than either bluffing or
staying quiet.

Then pivot to how you're closing the gap (below).

---

## 6. Close the gaps (study plan)

> 📅 **This section says *what*. [WEEKLY.md](WEEKLY.md) says *when*** — an exact five-hour
> cadence, applications from week 3, and an evidence-based CKA booking gate.

Highest leverage next steps to become clearly hireable, in order:
0. **Start the job loop immediately.** Week 1 produces a CV outline, week 2 an honest GitHub
   project page and learner-owned changelog, and week 3 starts two targeted applications per
   week. The capstone improves later applications; it does not grant permission to begin.
1. **Finish the common operating core.** Git, Bash, Linux and DNS/TCP/TLS/HTTP diagnosis come
   before specialist controllers. Follow the Common core dashboard filter and pass each
   milestone gate in [CURRICULUM.md](CURRICULUM.md).
2. **One cloud, deep: AWS.** Labs 16/39/40 Part A establish Terraform state, IAM, VPC, S3,
   audit and cost controls; labs 25/40 Part B add EKS, workload identity, RDS and GitOps.
   Use GitHub OIDC rather than stored access keys.
3. **Drill required outcomes.** A library of authored labs with little recall is weaker than
   a smaller core you can reproduce. [DRILLS.md](DRILLS.md) covers required core and selected
   specialization labs; electives can remain reference-only.
4. **Choose, then certify.** Select Platform/CKA only when target roles support it. Pass
   [lab 48](../labs/48-cka-exam-readiness/) at 8/10 inside 45 minutes twice on different weeks,
   then book four to six weeks out and pass a full 120-minute simulator before the exam.
5. **Stop extending this repo.** The subject-area breadth is done. Resume authoring only when
   repeated job-description or interview evidence exposes a specific gap.

---

## 7. LLMOps — the AI/infra differentiator

The second project ([ai-assistant/](../ai-assistant/)) matters as AI-infra demand grows. The
30-second pitch: *"A private RAG assistant over our own docs — local LLM via Ollama
(LM Studio-compatible), Qdrant vectors, a FastAPI service with streaming, grounding guardrails,
token/cost and per-stage metrics, a semantic cache, a tool-calling agent that operates the main
Dojo app's API, and an eval harness with prompt-injection tests that gates releases. Swapping
the model backend is one env var."* The job-relevant framing is **operating** inference, not
training models. Rehearse these:

**Q: How is running an LLM service different from a normal web service?**
> Outputs are nondeterministic, so "tests" are a threshold-based eval suite, not assertions;
> cost is per-token, not per-request; latency is dominated by the model, and quality can
> regress with *no code change* (a prompt or model swap). That's why I built an eval, token
> metrics, and prompt versioning — the things that make those differences observable.

**Q: How do you monitor it?**
> The golden signals plus LLM-specific ones, by name: `dojo_ai_chat_latency_seconds` and
> `dojo_ai_time_to_first_token_seconds` (TTFT is what users feel), `dojo_ai_stage_latency_seconds{stage}`
> to see whether embed, retrieval, or generation is the bottleneck, `dojo_ai_tokens_total` for
> cost, and grounded-rate from `dojo_ai_chat_requests_total{grounded}`. Plus JSON logs with a
> request ID so one slow request is greppable.

**Q: How do you stop it hallucinating?**
> Retrieval-score gate (`MIN_SCORE`): if the best chunk is too weak the app refuses with no
> sources instead of guessing; the prompt says "answer only from context and cite [n]"; and the
> eval has must-refuse and prompt-injection cases so a regression fails CI. I'm honest that a
> gate reduces, not eliminates, hallucination.

**Q: How do you control cost?**
> Token accounting from the API's `usage` (with a labeled estimate fallback when a backend
> omits it), a Grafana panel that prices those tokens at hosted-API rates, a semantic cache so
> near-duplicate questions skip generation entirely (`dojo_ai_cache_events_total` hit ratio),
> and prompt-budget levers — `TOP_K`, `HISTORY_TURNS`, chunk size.

**Q: How do you CI/CD an app with nondeterministic output?**
> Two tiers. Fast deterministic gate on every PR: pytest over the *pure* functions (chunking,
> MMR, grounding decision, prompt build) + route tests + a Trivy CRITICAL gate + image build.
> Then a nightly live eval against a real (small) model with a pass threshold, a per-category
> report published to the run summary, and prompt A/B before a prompt change ships.

**Q: Explain tool calling and its risks.**
> An agent is a bounded loop: hand the model tool schemas, execute any `tool_calls` it returns,
> feed results back, repeat up to a turn limit. Risks are unbounded loops, unwanted writes, and
> slow tools — so mine caps turns, keeps write tools behind a flag (read-only by default), sets
> per-tool timeouts, and counts every call. My agent calls the main Dojo API, so it reads real
> progress data. MCP is the same idea with a standardized transport.

**Q: You ran a local model — what changes with GPUs / at scale?**
> The `OPENAI_BASE_URL` abstraction means swapping Ollama for vLLM or a hosted API is config,
> not code. On K8s you'd schedule `nvidia.com/gpu` (the manifest has the stub), and you'd reach
> for vLLM because batching and KV-cache reuse are what make GPU serving efficient. Right-size
> the model too — I run a 1b model in CI and a 3b locally for exactly that reason.

### Quick self-test

Can you, without notes: draw the architecture, explain liveness vs readiness, describe your CI
stages, define GitOps and its benefits, and say what you'd change for production? If yes,
you're interview-ready for junior/associate DevOps, Platform, and SRE roles.

---

## 8. Fundamentals screener (the round before the round)

Many pipelines start with a 20-minute quick-fire on networking and Linux — it filters people
*before* anyone asks about Kubernetes. Every answer below is grounded in this project, so you
can always continue with "…and in my project that's exactly the X hop."

**Q: What happens when you open `https://dojo.example.com`?** Walk the layers, in order:
> 1. **DNS**: browser cache → OS cache/`hosts` file → the configured resolver, which walks
>    root → TLD → authoritative and returns the A/AAAA record (my EC2 IP).
> 2. **TCP**: three-way handshake (SYN, SYN-ACK, ACK) to port 443.
> 3. **TLS**: handshake — server presents its cert (mine is issued by Let's Encrypt via
>    Caddy, in-cluster by cert-manager), client verifies the chain, they agree keys.
> 4. **HTTP**: request hits **Caddy** (reverse proxy), which routes `/` to the **nginx**
>    container serving the React build and `/api` to the **Go API**, which queries
>    **Postgres** (through a Redis cache) and returns JSON.
> Naming each hop matters because that's the 502-debugging path in reverse (§3). *(The
> in-cluster continuation of this story — ClusterIP, kube-proxy, CoreDNS, the Gateway path —
> is drilled hands-on in [lab 49](../labs/49-k8s-networking-deep-dive/).)*

**Q: TCP vs UDP?**
> TCP: connection, ordering, retransmission — HTTP, Postgres, Redis: everything in my stack.
> UDP: fire-and-forget, no handshake — DNS queries, metrics agents (statsd), streaming.
> Follow-up they like: HTTP/3 runs over UDP (QUIC) and reimplements reliability in userspace.

**Q: How does DNS work *inside* your stack?**
> Twice over. Docker's embedded DNS (`127.0.0.11`) resolves Compose service names — my nginx
> proxies to `http://api:8080` by service name. In Kubernetes, CoreDNS resolves
> `api.devops-dojo.svc.cluster.local` to the Service's ClusterIP. Same idea, different resolver
> — and "the app can't reach the DB" is a DNS/NetworkPolicy question before it's an app question.

**Q: Explain the HTTP status codes you've actually dealt with.**
> `200/201` fine; `301/308` redirects (Caddy HTTP→HTTPS); `401` no credentials vs `403`
> authenticated-but-forbidden (RBAC, lab 27); `404` wrong path (my nginx `/api` proxy strip);
> `499` client gave up (k6 timeouts, lab 20); `502` proxy can't reach upstream (dead api
> container); `503` upstream alive but not ready (readiness probe failing — lab 08); `504`
> upstream too slow (DB lock drill, lab 35).

**Linux triage one-liners** (drill until automatic — deeper walkthrough in
[LINUX_FOR_CONTAINERS.md](LINUX_FOR_CONTAINERS.md)):

| Symptom | First commands | What you're distinguishing |
|---|---|---|
| "Server is slow" | `uptime`, `top` | load (runnable queue) vs CPU%; I/O wait vs compute |
| Out of memory? | `free -m`, `dmesg \| grep -i oom` | cache (fine) vs real exhaustion; did the OOM-killer strike |
| Disk full | `df -h`, `du -xh --max-depth=1 /var \| sort -h` | which mount, which directory (usually logs or Docker) |
| Port in use / is it listening? | `ss -tlnp` | nothing listening (app down) vs listening on wrong interface |
| Runaway process | `ps aux --sort=-%cpu \| head` | who, and is it yours |
| Service died | `systemctl status X`, `journalctl -u X -n 50` | crashed vs never started vs restart-looping |

The container versions of these are lab 35's bread and butter: `kubectl top`, `kubectl logs
--previous`, `docker stats`, `kubectl describe` events. The host versions are drilled for real
in [lab 54](../labs/54-linux-server-ops/).

**Q: How do you make a service start on boot, and how do you read its logs?**
> A **systemd unit**, not a `restart:` policy — Docker's restart policy brings a container back
> when the daemon is up; it does nothing about "nobody ran `compose up` after the reboot". Mine
> is `Type=oneshot` with `RemainAfterExit=yes`, because the command *starts* something and
> exits — with `Type=simple` systemd watches `docker compose up -d` return immediately and
> declares the unit dead. `Requires=docker.service` is the dependency, `After=` is the
> ordering; you need both, since `Requires` alone lets them start in parallel. Logs are
> `journalctl -u dojo`, and the flags that matter in an incident are `--since "10 min ago"`,
> `-p err`, and **`-b -1`** — the previous boot, which is the only way to answer "it died
> overnight and the box rebooted".

**Follow-up — Q: cron or a systemd timer?**
> Timer, for three concrete reasons: `Persistent=true` runs a missed job after downtime (cron
> just skips it), `RandomizedDelaySec` stops a fleet from stampeding on the hour, and output
> lands in the journal with the unit's retention instead of a `>> /var/log/x.log` that nobody
> rotates. It also splits schedule from work, so I can run the job now with
> `systemctl start x.service` without touching the schedule, and `systemctl list-timers` shows
> me when it fires next — which cron cannot.

**Q: `df` says the disk is full, `du` says it isn't. What's going on?** *(a favourite)*
> A **deleted-but-still-open** file. The blocks aren't freed until the last file descriptor
> closes, so the space is gone while the *name* is not — `du` walks the directory tree and
> can't see it; `df` reads the filesystem's allocation and can. Find it with `sudo lsof +L1`
> (link count 0), or `ls -l /proc/*/fd | grep deleted` if lsof isn't installed. `rm` won't help:
> restart or kill the process holding it. Classic cause is a logfile rotated without
> `copytruncate` while the writer kept the handle — which is exactly the `logrotate` config I
> ship for the Docker json logs.

---

## 9. System design round (mid-level gatekeeper)

Structure beats brilliance: **requirements → the boring working version → what changes at
scale → trade-offs, named unprompted.** Both classics below are answerable *from this repo* —
you've built the small version of each.

### "Design CI/CD for a team with 20 microservices."

> **Requirements first:** how often do we ship, what's the rollback story, what must never
> reach prod (unscanned/unsigned images), who approves what.
> **The boring version (mine, scaled):** one pipeline *template* — a reusable workflow /
> Jenkins Shared Library (labs 15/24/43) so 20 repos don't copy-paste — that builds once,
> tests, Trivy-gates, signs with cosign (lab 41), pushes an immutable digest to the registry.
> Delivery is **pull-based GitOps**: an ArgoCD ApplicationSet (labs 25/36) stamps out
> dev/staging/prod per service from one chart + values-per-env; **promotion is a PR** bumping
> a pinned tag, prod syncs manually or behind an approval; rollback is `git revert`. Canary
> via Argo Rollouts (lab 32) for the risky services.
> **At scale you add:** build caching + a runner fleet, preview environments per PR,
> secrets from a real manager via External Secrets (lab 26), drift detection, and org-wide
> admission policies (Kyverno, lab 29) as the backstop when a team bypasses the template.
> **Trade-offs to name:** push vs pull deploys (credentials live in the cluster, not CI);
> monorepo vs polyrepo (template reuse vs blast radius); speed vs gates (that's what the
> error budget arbitrates, §2).

### "Design observability for a microservices platform."

> **Requirements first:** MTTD/MTTR targets, who gets paged, retention and cost limits.
> **The boring version (mine, scaled):** the three pillars, one UI. **Metrics**: every service
> exposes Prometheus histograms; RED (rate/errors/duration) per service — that's my
> `dojo_http_*` metrics generalized; collected by the Prometheus Operator via ServiceMonitors
> (lab 34). **Logs**: structured JSON to stdout, shipped by Grafana Alloy to Loki —
> never `exec` into pods to read files. **Traces**: OpenTelemetry SDK, context propagated on
> every hop, sent to Tempo — trace-ID in the logs links all three. **Alerting**: SLO
> burn-rate alerts (§2) to Alertmanager, which groups, dedupes, and routes — page only on
> user-facing symptoms; everything else is a ticket.
> **At scale you add:** trace **sampling** (head vs tail — tail keeps the interesting errors,
> costs a buffer), **cardinality control** (a `user_id` label will melt Prometheus; that's
> what exemplars and traces are for), retention tiers (hot vs object storage — Loki/Tempo
> already do this), and federation/Thanos when one Prometheus isn't enough.
> **Trade-offs to name:** alert fatigue vs coverage (symptom-based paging), metric cost vs
> insight (labels are the price), and "observability ≠ dashboards" — it's being able to ask
> new questions without shipping new code.

---

## 10. Mock-interview protocol (run it weekly)

Rehearsing alone beats re-reading. One 40-minute loop, timer visible, **answers spoken out
loud** — the gap between "I know this" and "I can say this" is exactly what interviews measure.
Record yourself once; it's uncomfortable and worth it.

1. **Quick-fire — 10 min.** Six questions picked blind from §2/§8 (roll a die twice). No notes.
   Pass: 5/6 answered in under a minute each.
2. **Live incident — 20 min.** `scripts/chaos/roulette.sh` (lab 35) breaks your own stack
   blind. Narrate the method as you go — *observe → hypothesize → verify → fix → confirm* —
   as if the interviewer were watching your screen. Pass: root cause **and** fix inside 20
   minutes, method narrated, three-line postmortem written.
   *(Host-level variant: `scripts/chaos/fill-disk.sh` from lab 54 — same loop, no `kubectl`.)*
3. **Design — 10 min.** One question from §9, sketched on paper while talking. Pass: you named
   at least two trade-offs *without being prompted*.

This consumes the weekly recall block in [WEEKLY.md](WEEKLY.md). The mock loop tests whether
you can *talk*; the drills test whether you can *produce*. Interviews ask for both.

**Interview-loop criterion:** two consecutive clean loops mean the rehearsal is working; keep
applying and keep the loop running during the search. Pair this with the
[common core](DOCKER_LEARNING_PATH.md#the-job-first-common-core): interviews, applications and
remaining depth run in parallel, not in sequence.

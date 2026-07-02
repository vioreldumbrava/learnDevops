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
> and Caddy becomes an Ingress.

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

### Observability — the three pillars

**Q: How would you debug a slow endpoint in production?**
> Metrics first (Prometheus/Grafana) to see *what and how often* — request rate, error rate,
> p95 latency from my `/metrics`. Logs next (Loki) to see *what happened* — I query
> `{compose_service="api"} | json | status>=400`. Traces (Tempo) to see *where the time went* —
> my traces show a `store.*` DB span nested in the request span, so I can tell app vs DB time.
> Alertmanager pages me before users notice via rules like error-rate and p95 thresholds.

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

**"The site is up but returns 502."** Work the path: client → LB/Ingress → Service →
Pod/readiness. Is the ingress controller healthy? Do Service endpoints exist (readiness
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
  understand the trade-offs at each layer — which I documented as 25 hands-on labs."

---

## 5. Weaknesses — name them before they do

Interviewers respect honesty over bluffing:
- "My production experience is from this project, not yet a high-traffic system on-call —
  but I've drilled incident response deliberately: eight break-fix scenarios on my own
  cluster, with runbooks and written postmortems (lab 35)."
- "I've run Kubernetes on kind and EKS, but haven't operated a large multi-team cluster."
- "Local/dev uses a demo password for convenience — but the chart supports `secrets.create=false`
  so real deployments get `dojo-secrets` from **Sealed Secrets** or the **External Secrets
  Operator** (lab 26), keeping plaintext out of Git." *(A gap I already closed — turn it into a
  strength.)*
Then pivot to how you're closing the gap (below).

---

## 6. Close the gaps (study plan)

Highest leverage next steps to become clearly hireable, in order:
1. **CKA first.** Labs 22–34 already cover most of the exam surface, so it's the cheapest
   high-recognition credential from where you stand — and the strongest CV filter-pass for
   Platform/DevOps roles in Europe. Book the exam date now; a deadline beats an intention.
   Add **CKS** later if you're targeting security-leaning roles.
2. **One cloud, deep:** AWS — VPC/subnets/IAM, RDS, S3, ELB, autoscaling. Labs 16/25/**40**
   are the hands-on base; target the **AWS Solutions Architect Associate** cert after CKA.
3. **Scripting:** covered in lab **37** (Bash strict mode, Python, boto3, jq/awk) — keep
   every new piece of glue in `scripts/`, shellcheck-clean, so the habit shows.
4. **Secrets management:** done in lab 26 (Sealed Secrets / External Secrets Operator) — go
   further with Vault dynamic secrets and automatic rotation.
5. **Keep extending this repo** and write short posts on each capstone step; visible learning
   is a hiring signal.

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

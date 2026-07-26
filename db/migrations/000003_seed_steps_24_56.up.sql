-- Seed labs 24-56: the tracks added after the original 24-lab roadmap.
-- Idempotent: safe to run more than once (same ON CONFLICT upsert as 000002).
--
-- sort_order is the *intended study order* from docs/CURRICULUM.md, which is not the
-- folder-number order: lab 24 (Jenkins) belongs to Milestone 2, and labs 48/49/51/52/53
-- belong to the Kubernetes deep-dive. The frontend groups by milestone in the order the
-- rows arrive, so this column alone drives the dashboard's layout.
--
-- milestone: 1 foundation · 2 delivery · 3 cloud/scale/k8s · 4 operate & automate
--            5 ecosystem breadth · 6 kubernetes deep-dive · 7 polyglot extra

INSERT INTO steps (id, lab_no, title, topic, maps_to, milestone, doc_path, summary, sort_order) VALUES
-- Milestone 2 — delivery (joins labs 13-17 in the dashboard)
('24-jenkins',                 24, 'Self-hosted CI/CD with Jenkins','Jenkinsfile, agents, credentials',   '§12',   2, 'labs/24-jenkins/',                 'The same pipeline as lab 15, but on infrastructure you own.',                  24),

-- Milestone 3 — cloud, scale & Kubernetes (joins labs 18-23)
('25-capstone-eks-gitops',     25, 'Capstone: EKS + GitOps',       'Terraform EKS + ArgoCD',              'all',   3, 'labs/25-capstone-eks-gitops/',     'Commit to a self-healing Kubernetes deployment on AWS. Interview centerpiece.', 25),
('26-secrets-management',      26, 'Production secrets',           'Sealed Secrets / External Secrets',   '§17+',  3, 'labs/26-secrets-management/',      'Populate dojo-secrets from outside Git; no plaintext in the repo.',            26),

-- Kubernetes deep-dive track (Platform/SRE · CKA/CKS)
('27-k8s-rbac',                27, 'RBAC & least privilege',       'ServiceAccounts, Roles, Bindings',    'CKA/CKS',6,'labs/27-k8s-rbac/',                'Scope a workload to exactly what it needs; prove it with auth can-i.',         27),
('28-k8s-network-policies',    28, 'NetworkPolicies',              'Zero-trust with Calico',              'CKA/CKS',6,'labs/28-k8s-network-policies/',    'Default-deny plus explicit allows between tiers.',                             28),
('29-k8s-kyverno',             29, 'Policy-as-code',               'Kyverno admission control',           'CKS',   6, 'labs/29-k8s-kyverno/',             'Reject bad manifests at admission: no :latest, require limits and labels.',    29),
('30-k8s-cert-manager',        30, 'cert-manager',                 'Automatic in-cluster TLS',            '—',     6, 'labs/30-k8s-cert-manager/',        'Issue and renew certificates without touching a server.',                      30),
('31-k8s-keda-autoscaling',    31, 'KEDA autoscaling',             'Event-driven scaling on queue depth', '—',     6, 'labs/31-k8s-keda-autoscaling/',    'Scale the worker on Redis queue depth — even to zero.',                        31),
('32-k8s-argo-rollouts',       32, 'Argo Rollouts',                'Canary & blue-green delivery',        '—',     6, 'labs/32-k8s-argo-rollouts/',       'Progressive delivery with pause, promote and abort.',                          32),
('33-k8s-velero-backup',       33, 'Velero backup & DR',           'Cluster-state backup/restore',        '—',     6, 'labs/33-k8s-velero-backup/',       'Schedule a namespace backup, then actually restore it.',                       33),
('34-k8s-kube-prometheus-stack',34,'kube-prometheus-stack',        'Prometheus Operator, ServiceMonitor', '—',     6, 'labs/34-k8s-kube-prometheus-stack/','Cluster-wide monitoring the way real clusters run it.',                       34),
('49-k8s-networking-deep-dive',49, 'Networking data plane',        'veth, ClusterIP, kube-proxy, CoreDNS','CKA/CKS',6,'labs/49-k8s-networking-deep-dive/','Read the DNAT rules off a node; trace a packet from DNS to pod.',              35),
('51-k8s-cilium-ebpf',         51, 'Cilium / eBPF',                'kube-proxy-free, Hubble, L7 policy',  'CKA/CKS',6,'labs/51-k8s-cilium-ebpf/',         'The same data plane in eBPF maps, narrated by Hubble.',                        36),
('52-k8s-storage',             52, 'Storage',                      'StorageClass, PV/PVC, reclaim',       'CKA',   6, 'labs/52-k8s-storage/',             'Dynamic vs static provisioning, WaitForFirstConsumer, Delete vs Retain.',      37),
('53-k8s-scheduling',          53, 'Scheduling',                   'Requests, taints, affinity, spread',  'CKA',   6, 'labs/53-k8s-scheduling/',          'Who put every pod where it is — plus a timed three-fault break-fix.',          38),
('48-cka-exam-readiness',      48, 'CKA exam readiness',           'etcd restore, drains, kubelet',       'CKA',   6, 'labs/48-cka-exam-readiness/',      'The cluster-operations half of the exam, ending in a timed mock.',             39),

-- Milestone 4 — operate, automate & prove it
('35-incident-response',       35, 'Incident response',            'Break-fix drills, runbooks',          'extra', 4, 'labs/35-incident-response/',       'Eight scripted failures on your own cluster. Interview centerpiece #2.',       40),
('36-multi-env-promotion',     36, 'Multi-env promotion',          'ApplicationSet, values-per-env',      'extra', 4, 'labs/36-multi-env-promotion/',     'dev/staging/prod from one chart; promotion is a pull request.',                41),
('37-scripting-automation',    37, 'Bash & Python automation',     'Strict mode, jq/awk, boto3',          'extra', 4, 'labs/37-scripting-automation/',    'Backup rotation, wait-for-healthy, restore verification, log drills.',         42),
('38-git-workflows',           38, 'Git workflows',                'Rebase, conflicts, bisect',           'extra', 4, 'labs/38-git-workflows/',           'PR flow, a manufactured conflict, and bisect on a planted bug.',               43),
('39-terraform-state-and-modules',39,'Terraform state & modules',  'S3 backend, locking, tflint',         'extra', 4, 'labs/39-terraform-state-and-modules/','Remote state with locking, a reusable module, IaC checks in CI.',           44),
('40-aws-core-services',       40, 'AWS core services',            'RDS, S3 lifecycle, IAM/IRSA, VPC',    'extra', 4, 'labs/40-aws-core-services/',       'Managed data services and AWS access with zero stored keys.',                  45),
('41-supply-chain-security',   41, 'Supply-chain security',        'cosign keyless, admission verify',    'extra', 4, 'labs/41-supply-chain-security/',   'Sign images in CI; refuse unsigned ones at admission.',                        46),
('42-gitlab-ci',               42, 'GitLab CI',                    '.gitlab-ci.yml',                      'extra', 4, 'labs/42-gitlab-ci/',              'The same pipeline translated; GitLab is everywhere in EU postings.',           47),
('54-linux-server-ops',        54, 'Linux server operations',      'systemd, journald, SSH, disk triage', 'extra', 4, 'labs/54-linux-server-ops/',        'Own the box under the containers: units, timers, logs, a full disk.',          48),
('55-postgres-operations',     55, 'Postgres under load',          'EXPLAIN, locks, pooling, vacuum',     'extra', 4, 'labs/55-postgres-operations/',     'Diagnose and fix a slow database — the most common real incident.',            49),
('56-slo-and-error-budgets',   56, 'SLOs & error budgets',         'Burn-rate alerting, budget policy',   'extra', 4, 'labs/56-slo-and-error-budgets/',   'Turn three static alerts into multi-window burn-rate paging.',                 50),

-- Polyglot extra
('50-go-vs-python-parity',     50, 'Go vs Python parity',          'One contract, two implementations',   'extra', 7, 'labs/50-go-vs-python-parity/',     'Hot-swap the API language; the contract is the interface.',                    51),

-- Milestone 5 — ecosystem breadth & portability
('43-jenkins-shared-library',  43, 'Jenkins Shared Library',       'Reusable steps, webhooks, versioning','extra', 5, 'labs/43-jenkins-shared-library/',  'Stop fifty Jenkinsfiles from copy-pasting the same build logic.',              52),
('44-ansible-at-scale',        44, 'Ansible at scale',             'Dynamic inventory, roles',            'extra', 5, 'labs/44-ansible-at-scale/',        'Target servers by tag instead of pasting IPs; split into roles.',              53),
('45-boto3-ops-automation',    45, 'Boto3 ops automation',         'Snapshot lifecycle, self-healing',    'extra', 5, 'labs/45-boto3-ops-automation/',    'EBS snapshots by tag and a monitor that restarts what it finds down.',         54),
('46-helm-library-chart',      46, 'Helm library chart + Helmfile','type: library, push-based multi-env', 'extra', 5, 'labs/46-helm-library-chart/',      'Write the Deployment shape once; Helmfile as ArgoCD''s push-based twin.',      55),
('47-cloud-portability-aks',   47, 'Cloud portability: AKS',       'The unchanged chart on Azure',        'extra', 5, 'labs/47-cloud-portability-aks/',   'Prove the chart transfers; keep the provider map as the interview answer.',    56)
ON CONFLICT (id) DO UPDATE SET
    lab_no = EXCLUDED.lab_no, title = EXCLUDED.title, topic = EXCLUDED.topic,
    maps_to = EXCLUDED.maps_to, milestone = EXCLUDED.milestone, doc_path = EXCLUDED.doc_path,
    summary = EXCLUDED.summary, sort_order = EXCLUDED.sort_order;

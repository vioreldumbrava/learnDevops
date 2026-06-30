-- Seed the full 24-lab roadmap. Idempotent: safe to run more than once.

INSERT INTO steps (id, lab_no, title, topic, maps_to, milestone, doc_path, summary, sort_order) VALUES
('00-prerequisites',        0,  'Prerequisites & repo tour',     'Setup & tooling',                '—',    1, 'labs/00-prerequisites/',        'Install Docker, learn the repo layout, init git.',                          0),
('01-docker-basics',        1,  'Docker basics',                 'Images, containers, layers',     '§1',   1, 'labs/01-docker-basics/',        'Build and run the API image; understand images vs containers vs layers.',   1),
('02-containerize-api',     2,  'Containerize the API',          'Multi-stage, distroless, non-root','§2-3', 1, 'labs/02-containerize-api/',     'Tiny secure Go image; bind mounts vs COPY.',                                2),
('03-containerize-frontend',3,  'Containerize the frontend',     'Multi-stage build to Nginx',     '§5',   1, 'labs/03-containerize-frontend/','Build React with Vite, serve static files via Nginx.',                      3),
('04-docker-compose',       4,  'Docker Compose',                'Multi-service, DNS, networks, volumes','§4',1,'labs/04-docker-compose/',      'Run api+db+frontend together; service discovery by name.',                  4),
('05-dev-prod-compose',     5,  'Dev/prod Compose separation',   'Overrides & overlays',           '§6',   1, 'labs/05-dev-prod-compose/',     'Hot-reload dev vs Caddy/restart-policy prod via -f overlays.',               5),
('06-database-migrations',  6,  'Database & migrations',         'golang-migrate + Postgres',      '§7',   1, 'labs/06-database-migrations/',  'Version your schema; run migrations as a one-shot service.',                 6),
('07-backup-restore',       7,  'Backups & restore',             'pg_dump / pg_restore',           '§8',   1, 'labs/07-backup-restore/',       'Back up and restore the database volume safely.',                            7),
('08-health-checks',        8,  'Health checks',                 'Liveness vs readiness',          '§9',   1, 'labs/08-health-checks/',        'Why /healthz and /readyz differ; depends_on healthy.',                       8),
('09-cache-and-worker',     9,  'Cache + background worker',     'Redis cache & job queue',        'extra',1, 'labs/09-cache-and-worker/',     'Cache reads; offload work to a worker via a Redis queue.',                   9),
('10-monitoring',           10, 'Monitoring',                    'Prometheus + Grafana',           '§10',  1, 'labs/10-monitoring/',           'Scrape real /metrics, build a Grafana dashboard.',                           10),
('11-logging',              11, 'Logging',                       'Loki + Promtail',                '§11',  1, 'labs/11-logging/',              'Centralize structured logs and query them in Grafana.',                      11),
('12-tracing-and-alerting', 12, 'Tracing + Alerting',            'OTel/Tempo + Alertmanager',      'extra',1, 'labs/12-tracing-and-alerting/', 'Distributed traces and alert rules: the rest of observability.',             12),
('13-image-registry',       13, 'Image registry',                'ghcr.io, tags, SBOM',            '§13',  2, 'labs/13-image-registry/',       'Tag, version and push images; generate an SBOM.',                            13),
('14-artifact-repository',  14, 'Artifact repository',           'Artifactory / Nexus',            '§14',  2, 'labs/14-artifact-repository/',  'Store build artifacts in a real repository manager.',                        14),
('15-cicd',                 15, 'CI/CD',                         'GitHub Actions',                 '§12',  2, 'labs/15-cicd/',                 'Build, test, scan, push and deploy automatically.',                          15),
('16-terraform',            16, 'Infrastructure as Code',        'Terraform',                      'extra',2, 'labs/16-terraform/',            'Provision a VPS/EC2 from code.',                                             16),
('17-ansible',              17, 'Configuration management',      'Ansible',                        'extra',2, 'labs/17-ansible/',              'Configure the server and deploy the stack repeatably.',                      17),
('18-deploy-https',         18, 'Deploy to VPS/EC2 + HTTPS',     'Caddy auto-TLS',                 '§15-16',3,'labs/18-deploy-https/',         'Public deployment with automatic HTTPS.',                                    18),
('19-security',             19, 'Security hardening',            'non-root, scans, secrets',       '§17',  3, 'labs/19-security/',             'Harden images and compose; scan with Trivy/Scout.',                          19),
('20-load-testing',         20, 'Load testing',                  'k6',                             '§18',  3, 'labs/20-load-testing/',         'Drive load and read latency/error thresholds.',                              20),
('21-scaling',              21, 'Horizontal scaling',            'Scale behind Caddy',             '§19',  3, 'labs/21-scaling/',              'Run multiple stateless replicas; stateless vs stateful.',                    21),
('22-kubernetes',           22, 'Kubernetes on kind',            'Deployments, Services, Ingress', '§20',  3, 'labs/22-kubernetes/',           'Move the stack to a local Kubernetes cluster.',                              22),
('23-helm',                 23, 'Helm packaging',                'Helm charts',                    'extra',3, 'labs/23-helm/',                 'Package the manifests as a reusable Helm chart.',                            23)
ON CONFLICT (id) DO UPDATE SET
    lab_no = EXCLUDED.lab_no, title = EXCLUDED.title, topic = EXCLUDED.topic,
    maps_to = EXCLUDED.maps_to, milestone = EXCLUDED.milestone, doc_path = EXCLUDED.doc_path,
    summary = EXCLUDED.summary, sort_order = EXCLUDED.sort_order;

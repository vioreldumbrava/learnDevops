// Lab 55 — load that lands on the DATABASE, not on the Redis cache.
//
// deploy/load-test/load-test.js hammers /api/steps, which is cached for 30s — great for
// measuring the HTTP path, useless for measuring Postgres. This one deliberately does the
// opposite: every read targets a different step (so the notes query runs for real) and a
// share of iterations WRITE, which invalidates the steps cache and forces the next read
// through to the database.
//
// The trailing `run /scripts/db-load.js` overrides the service's default command, which
// points at load-test.js:
//
//   docker compose -f deploy/compose/compose.yaml \
//                  -f deploy/compose/compose.pgtune.yaml \
//                  run --rm -e VUS=50 -e DURATION=2m load-test run /scripts/db-load.js
//
// Two profiles:
//   default          steady load — use this while reading pg_stat_statements
//   BURST=1          a spike from 5 to 200 VUs — the connection-exhaustion drill
import http from 'k6/http'
import { check, sleep } from 'k6'

const TARGET = __ENV.TARGET_URL || 'http://api:8080'
const BURST = __ENV.BURST === '1'
const WRITE_RATIO = Number(__ENV.WRITE_RATIO || 0.2)

// Spread reads across many steps so no single row stays hot in cache.
const STEPS = [
  '00-prerequisites', '01-docker-basics', '04-docker-compose', '06-database-migrations',
  '10-monitoring', '15-cicd', '22-kubernetes', '25-capstone-eks-gitops',
  '35-incident-response', '48-cka-exam-readiness',
]

export const options = BURST
  ? {
      // Ramp hard enough to exhaust max_connections=25, then hold, then recover.
      stages: [
        { duration: '15s', target: 5 },
        { duration: '15s', target: 200 },
        { duration: '45s', target: 200 },
        { duration: '15s', target: 5 },
      ],
      // No thresholds: this profile is EXPECTED to fail before you add the pooler.
      // Compare the summary before and after — that comparison is the deliverable.
    }
  : {
      vus: Number(__ENV.VUS || 30),
      duration: __ENV.DURATION || '2m',
      thresholds: {
        http_req_failed: ['rate<0.01'],
        http_req_duration: ['p(95)<500'],
      },
    }

export default function () {
  const step = STEPS[Math.floor(Math.random() * STEPS.length)]

  const read = http.get(`${TARGET}/api/notes?step=${step}`, { tags: { op: 'notes_read' } })
  check(read, { 'notes read 200': (r) => r.status === 200 })

  if (Math.random() < WRITE_RATIO) {
    const write = http.post(
      `${TARGET}/api/notes`,
      JSON.stringify({ step_id: step, body: `load ${Date.now()} ${__VU}` }),
      { headers: { 'Content-Type': 'application/json' }, tags: { op: 'notes_write' } },
    )
    check(write, { 'notes write 2xx': (r) => r.status >= 200 && r.status < 300 })
  }

  sleep(BURST ? 0.1 : 0.5)
}

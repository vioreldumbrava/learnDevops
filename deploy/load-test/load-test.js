import http from 'k6/http'
import { check, sleep } from 'k6'

// Target defaults to the API over the Compose network. Override with -e TARGET_URL=...
const TARGET = __ENV.TARGET_URL || 'http://api:8080'

export const options = {
  vus: Number(__ENV.VUS || 10),
  duration: __ENV.DURATION || '30s',
  thresholds: {
    // The run FAILS (non-zero exit) if these are breached — that's the point.
    http_req_failed: ['rate<0.01'],   // <1% errors
    http_req_duration: ['p(95)<500'], // 95th percentile under 500ms
  },
}

export default function () {
  const res = http.get(`${TARGET}/api/steps`)
  check(res, { 'status is 200': (r) => r.status === 200 })
  sleep(1)
}

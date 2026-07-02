// Trivy scan, report-only (same policy as the lab-24 pipeline; pass exitCode: 1 to gate).
def call(String image, Map opts = [:]) {
  def severity = opts.get('severity', 'CRITICAL,HIGH')
  def exitCode = opts.get('exitCode', 0)
  sh """docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest \
        image --severity ${severity} --ignore-unfixed --exit-code ${exitCode} ${image}"""
}

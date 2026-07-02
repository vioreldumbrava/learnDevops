// True when the last commit message contains [ci skip]. Jenkins has no built-in
// skip-ci convention (GitHub Actions honors [skip ci] natively) — so the pipeline
// must check for its own version-bump commits or it triggers itself forever.
def call() {
  def msg = sh(script: 'git log -1 --pretty=%B', returnStdout: true).trim()
  return msg.contains('[ci skip]')
}

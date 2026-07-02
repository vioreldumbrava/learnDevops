// Commit the bumped VERSION file with a [ci skip] marker and push it back.
// Needs a username/password credential (GitHub username + PAT with repo:write).
// Secrets stay in shell variables — never interpolate them into Groovy strings,
// or they leak into the build log and Jenkins warns about it.
def call(String version, Map opts = [:]) {
  def credentialsId = opts.get('credentialsId', 'git-push-creds')
  def branch        = opts.get('branch', 'master')
  sh 'git config user.email "jenkins@dojo.local"'
  sh 'git config user.name "Jenkins CI"'
  sh 'git add VERSION'
  sh "git commit -m 'ci: bump version to ${version} [ci skip]'"
  withCredentials([usernamePassword(credentialsId: credentialsId,
                                    usernameVariable: 'GIT_USER',
                                    passwordVariable: 'GIT_TOKEN')]) {
    sh 'git push "$(git config --get remote.origin.url | sed "s#https://#https://$GIT_USER:$GIT_TOKEN@#")" ' +
       "HEAD:${branch}"
  }
}

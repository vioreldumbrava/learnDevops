// Build one image: buildImage('devops-dojo/api', './app/api', '0.1.4')
def call(String name, String context, String tag) {
  sh "docker build -t ${name}:${tag} ${context}"
}

// Self-hosted CI/CD pipeline (lab 24) — the Jenkins counterpart to
// .github/workflows/ci.yml. Point a Jenkins Pipeline job at this repo and it
// runs on every build. Per-stage `docker` agents share the workspace via the
// Docker Pipeline plugin, so no host-path mounting is needed (DooD-safe).
pipeline {
  agent none
  options {
    timestamps()
    disableConcurrentBuilds()
  }

  stages {
    stage('Test (Go)') {
      agent { docker { image 'golang:1.25' } }
      steps {
        dir('app/api') {
          sh 'go vet ./...'
          sh 'go test ./...'
        }
      }
    }

    stage('Build frontend') {
      agent { docker { image 'node:24-alpine' } }
      steps {
        dir('app/frontend') {
          sh 'npm ci'
          sh 'npm run build'
        }
      }
    }

    stage('Build images') {
      agent any
      steps {
        sh 'docker build -t devops-dojo/api:ci-$BUILD_NUMBER ./app/api'
        sh 'docker build -t devops-dojo/frontend:ci-$BUILD_NUMBER ./app/frontend'
      }
    }

    stage('Scan (Trivy)') {
      agent any
      steps {
        // Report only in this learning setup; use --exit-code 1 to gate the build.
        sh '''docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest \
              image --severity CRITICAL,HIGH --ignore-unfixed --exit-code 0 \
              devops-dojo/api:ci-$BUILD_NUMBER'''
      }
    }

    stage('Push') {
      agent any
      when { branch 'main' }
      steps {
        // Configure a "usernamePassword" credential (id: ghcr-creds) in Jenkins, then:
        //   withCredentials([usernamePassword(credentialsId: 'ghcr-creds', usernameVariable: 'U', passwordVariable: 'P')]) {
        //     sh 'echo "$P" | docker login ghcr.io -u "$U" --password-stdin'
        //     sh 'docker tag devops-dojo/api:ci-$BUILD_NUMBER ghcr.io/<owner>/<repo>/api:$BUILD_NUMBER'
        //     sh 'docker push ghcr.io/<owner>/<repo>/api:$BUILD_NUMBER'
        //   }
        echo 'On main: log in with a Jenkins credential and docker push here.'
      }
    }
  }

  post {
    always {
      node(null) {
        sh 'docker image rm devops-dojo/api:ci-$BUILD_NUMBER devops-dojo/frontend:ci-$BUILD_NUMBER || true'
      }
    }
  }
}

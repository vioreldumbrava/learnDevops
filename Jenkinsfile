// Self-hosted CI/CD pipeline (lab 24) — the Jenkins counterpart to
// .github/workflows/ci.yml. Point a Jenkins Pipeline job at this repo and it
// runs on every build. Per-stage `docker` agents share the workspace via the
// Docker Pipeline plugin, so no host-path mounting is needed (DooD-safe).
pipeline {
  // No default agent: each stage declares the tool image it needs, so the
  // Jenkins host needs NO Go/Node installed — same idea as GitHub's runners.
  agent none
  options {
    timestamps()              // prefix every log line — essential when comparing runs
    disableConcurrentBuilds() // two builds tagging ci-$BUILD_NUMBER images must not interleave
  }

  stages {
    // Fail fast: cheap checks first, so a broken test never wastes an image build.
    stage('Test (Go)') {
      agent { docker { image 'golang:1.25' } }   // same image the Dockerfile builds with
      steps {
        dir('app/api') {
          sh 'go vet ./...'    // static analysis: catches real bugs, not style
          sh 'go test ./...'
        }
      }
    }

    stage('Build frontend') {
      agent { docker { image 'node:24-alpine' } }
      steps {
        dir('app/frontend') {
          sh 'npm ci'          // ci (not install): exact lockfile versions, reproducible
          sh 'npm run build'   // includes `tsc` — the frontend's type check
        }
      }
    }

    // ci-$BUILD_NUMBER = a unique tag per run (Jenkins' answer to CI's type=sha
    // tags): parallel-safe, traceable back to the exact build in the UI.
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
    // A self-hosted runner keeps its disk between builds (unlike GitHub's
    // throwaway VMs) — without this cleanup, per-build images fill it up.
    // `|| true`: cleanup must never turn a green build red.
    always {
      node(null) {
        sh 'docker image rm devops-dojo/api:ci-$BUILD_NUMBER devops-dojo/frontend:ci-$BUILD_NUMBER || true'
      }
    }
  }
}

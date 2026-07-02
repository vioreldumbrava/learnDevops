#!/usr/bin/env bash
# bad-image.sh — drill 5: roll out an image tag that exists nowhere.
# Recover: kubectl -n devops-dojo rollout undo deploy/api   (or ./heal.sh)
set -euo pipefail
NS=devops-dojo

kubectl -n "$NS" set image deploy/api api=devops-dojo/api:v9.9.9
echo "Injected: rollout is stuck in ImagePullBackOff (old pods still serve). Start diagnosing."

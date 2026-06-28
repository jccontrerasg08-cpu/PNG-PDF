#!/usr/bin/env bash
set -euo pipefail

IMAGE="${1:-}"
TAG="${2:-latest}"

kubectl apply -k k8s/

if [[ -n "$IMAGE" ]]; then
  kubectl set image deployment/anythingintopdfbot anythingintopdfbot="$IMAGE:$TAG" -n anythingintopdfbot
fi

kubectl rollout status deployment/anythingintopdfbot -n anythingintopdfbot

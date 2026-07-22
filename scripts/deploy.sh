#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <image> [tag]" >&2
  echo "IMAGE is required so the deployment never falls back to the placeholder image in k8s/kustomization.yaml." >&2
  exit 1
fi

IMAGE="$1"
TAG="${2:-latest}"

kubectl apply -k k8s/
kubectl set image deployment/anythingintopdfbot anythingintopdfbot="$IMAGE:$TAG" -n anythingintopdfbot
kubectl rollout status deployment/anythingintopdfbot -n anythingintopdfbot

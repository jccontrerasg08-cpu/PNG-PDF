# Kubernetes deployment

This folder is ready to apply with Kustomize:

```bash
kubectl apply -k k8s/
```

## Where to put your image/API location

1. Put your built container image in `k8s/kustomization.yaml` under `images.newName` and `images.newTag`.
2. Put your public API hostname in `k8s/ingress.yaml` under `spec.rules[0].host`.
3. Keep the REST API path as `/api`: the app exposes `POST /api/convert` and `GET /api/supported-types`, and the browser UI posts to the same host with `/api/convert`.

Example:

```yaml
images:
  - name: anythingintopdfbot
    newName: registry.example.com/tools/anythingintopdfbot
    newTag: v1.0.0
```

```yaml
rules:
  - host: convert.example.com
```

After changing the image tag or host, redeploy with:

```bash
kubectl apply -k k8s/
kubectl rollout status deployment/anythingintopdfbot -n anythingintopdfbot
```

If you do not use an ingress controller, remove `ingress.yaml` from `k8s/kustomization.yaml` and expose the `anythingintopdfbot` Service with your platform's load balancer or gateway.


## GitHub-only deployment

The repository includes `.github/workflows/build-and-deploy.yml`. It pushes the image to GitHub Container Registry and, when the `KUBE_CONFIG` repository secret exists, applies this Kustomize folder to the cluster. Use this when you only have the repo locally and on GitHub.

## Optional deploy script

You can also redeploy with the helper script:

```bash
./scripts/deploy.sh registry.example.com/tools/anythingintopdfbot v1.0.0
```

The script applies `k8s/`, optionally updates the running Deployment image, and waits for the rollout.

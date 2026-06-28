# anythingintopdfbot

FastAPI web application and REST API for converting uploaded files into PDFs. The app is designed for containerized Kubernetes deployments and uses temporary filesystem storage only.

## Features

- Web upload page at `/`
- REST conversion endpoint at `/api/convert`
- Supported-types endpoint at `/api/supported-types`
- Health endpoint at `/healthz`
- Readiness endpoint at `/readyz`
- Modular converter architecture for PDFs, images, and simple text documents
- Dockerfile using Gunicorn with Uvicorn workers
- Kubernetes Deployment and Service manifests

## Supported conversions

| Module | Extensions | Behavior |
| --- | --- | --- |
| PDF | `.pdf` | Passes an uploaded PDF through the common conversion flow. |
| Images | `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`, `.tiff`, `.tif` | Converts image files to PDF with Pillow. |
| Documents | `.txt`, `.md` | Renders UTF-8 text-like documents to paginated PDFs with Pillow. |

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
uvicorn app.main:app --reload
```

Open <http://localhost:8000> to use the web UI.

## Tests

```bash
pytest
```

## Docker

```bash
docker build -t anythingintopdfbot:latest .
docker run --rm -p 8000:8000 anythingintopdfbot:latest
```


## API location

When deployed, the browser UI and REST API live on the same Kubernetes host. Put your public hostname in `k8s/ingress.yaml` at `spec.rules[0].host`; the REST API will then be available at:

- `POST https://YOUR_HOST/api/convert`
- `GET https://YOUR_HOST/api/supported-types`

Put your container registry image in `k8s/kustomization.yaml` under `images.newName` and `images.newTag`. The UI does not need a separate API URL because it submits to `/api/convert` on the same host.



## Deploy on Kuberns

This repo is ready for Kuberns. Kuberns can connect directly to your GitHub repo, detect the root-level `Procfile`, install dependencies from `requirements.txt`, and run the `web` service command.

1. Push this repository to GitHub.
2. Open the Kuberns dashboard and choose **Connect and Configure**.
3. Connect GitHub, select this repository and branch, and name the service `anythingintopdfbot`.
4. Select **Backend Service**.
5. You do not need environment variables for the current app.
6. Click **Deploy**.
7. After deployment, open the Kuberns-provided URL. The Web UI is `/`, and the API is `POST /api/convert`.

Kuberns deployment files in this repo:

- `Procfile` tells Kuberns how to start the FastAPI service.
- `runtime.txt` pins the Python runtime.
- `requirements.txt` lists the Python dependencies.

If Kuberns shows a custom run command field, use:

```bash
gunicorn app.main:app --worker-class uvicorn.workers.UvicornWorker --workers 2 --bind 0.0.0.0:$PORT
```

## Deploy from GitHub only

If this repo is only open here and on GitHub, push it to GitHub and use the included GitHub Actions workflow. On every push to `main`, `master`, or `work`, `.github/workflows/build-and-deploy.yml` builds the Docker image and pushes it to GitHub Container Registry as:

```text
ghcr.io/YOUR_GITHUB_USERNAME/anythingintopdfbot:latest
ghcr.io/YOUR_GITHUB_USERNAME/anythingintopdfbot:<commit-sha>
```

To let GitHub deploy to Kubernetes too, add this repository secret in GitHub:

- `KUBE_CONFIG`: the kubeconfig content for the Kubernetes cluster/service account that can deploy to the `anythingintopdfbot` namespace.

Then push to GitHub or run the workflow manually from **Actions → Build and deploy anythingintopdfbot → Run workflow**. If `KUBE_CONFIG` is not set, the workflow still builds and pushes the image, but it skips Kubernetes deployment.

## Deploy to Kubernetes

1. Build and push the image:

```bash
docker build -t YOUR_REGISTRY/anythingintopdfbot:latest .
docker push YOUR_REGISTRY/anythingintopdfbot:latest
```

2. Edit `k8s/kustomization.yaml` and replace `ghcr.io/YOUR_ORG/anythingintopdfbot` with your image repository.
3. Edit `k8s/ingress.yaml` and replace `anythingintopdfbot.example.com` with your public domain.
4. Deploy:

```bash
kubectl apply -k k8s/
kubectl rollout status deployment/anythingintopdfbot -n anythingintopdfbot
```

5. Open `https://YOUR_DOMAIN/` for the Web UI, or call `POST https://YOUR_DOMAIN/api/convert` for the REST API.

## Kubernetes

Apply the manifests after publishing the container image your cluster can pull:

```bash
kubectl apply -k k8s/
```

If you use a remote registry, update `k8s/kustomization.yaml` to reference that image instead of the `ghcr.io/YOUR_ORG/anythingintopdfbot:latest` placeholder. See `k8s/README.md` for redeploy instructions.

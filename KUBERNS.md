# Deploy anythingintopdfbot on Kuberns

Use this when your only deployment target is Kuberns and the code lives in GitHub.

## What Kuberns should detect

- `Procfile` declares the `web` service and starts FastAPI with Gunicorn/Uvicorn.
- `runtime.txt` requests the Python runtime.
- `requirements.txt` installs the app dependencies.

## Dashboard steps

1. Push this repository to GitHub.
2. Open the Kuberns dashboard.
3. Create a project or choose an existing project.
4. Choose **Backend Service**.
5. Connect your GitHub account if it is not already connected.
6. Select this repository and the branch you want to deploy.
7. Name the service `anythingintopdfbot`.
8. Leave environment variables empty for now; this app does not require any.
9. Click **Deploy**.
10. Use the generated Kuberns URL.

## API after deploy

If Kuberns gives you `https://anythingintopdfbot.example.kuberns.app`, then:

- Web UI: `https://anythingintopdfbot.example.kuberns.app/`
- Convert API: `POST https://anythingintopdfbot.example.kuberns.app/api/convert`
- Supported types: `GET https://anythingintopdfbot.example.kuberns.app/api/supported-types`
- Health check: `GET https://anythingintopdfbot.example.kuberns.app/healthz`
- Readiness check: `GET https://anythingintopdfbot.example.kuberns.app/readyz`

## Manual run command

If Kuberns asks for a run command instead of reading the `Procfile`, use:

```bash
gunicorn app.main:app --worker-class uvicorn.workers.UvicornWorker --workers 2 --bind 0.0.0.0:$PORT
```

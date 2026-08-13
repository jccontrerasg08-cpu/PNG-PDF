# Anything into PDF

Send a photo, Word file, spreadsheet, SVG, or note — get a PDF back. Use the website, the API, the CLI, or Telegram. Files are not persisted.

GitHub repo: [PNG-PDF](https://github.com/jccontrerasg08-cpu/PNG-PDF) · package: `anythingintopdfbot`

**GitHub About / topics** (Settings → General → Topics): `pdf` `converter` `telegram-bot` `fastapi` `heic` `libreoffice` `docker`  
Suggested description: `Anything into PDF — web, API, CLI, and Telegram. Send a file, get a PDF. Nothing is stored.`

## Quick start

On Debian/Ubuntu, install `python3-venv` first (`sudo apt install python3-venv`). SVG needs `libcairo2`; old `.doc` and layout-faithful Office need `libreoffice-writer`, `libreoffice-calc`, and `libreoffice-impress`.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
uvicorn app.main:app --reload
```

Open <http://localhost:8000>, drop files on the form, click **Convert to PDF**.

Or skip the server:

```bash
python -m app photo.png notes.txt
```

## Telegram

Copy `.env.example` to `.env` (gitignored) and paste your BotFather token:

```bash
cp .env.example .env
# TELEGRAM_BOT_TOKEN=123456:ABC
# TELEGRAM_BOT_USERNAME=YourBot   # optional; shows a t.me link on the homepage
python -m app.telegram
```

Then message the bot a photo or file. Same converter as the website.

On a public host, use a webhook instead of polling:

```bash
export TELEGRAM_BOT_TOKEN=123456:ABC
export TELEGRAM_WEBHOOK_SECRET=optional-shared-secret
curl "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  --data-urlencode "url=https://YOUR_HOST/telegram/webhook" \
  --data-urlencode "secret_token=$TELEGRAM_WEBHOOK_SECRET"
```

Without `TELEGRAM_BOT_TOKEN`, `/telegram/webhook` returns 404 and the web UI still works.

## What it converts

| Kind | Extensions | Behavior |
| --- | --- | --- |
| PDF | `.pdf` | Passes through files that contain `%PDF-` in the first 1KB. |
| Images | `.png` `.jpg` `.jpeg` `.webp` `.bmp` `.tiff` `.tif` `.gif` `.heic` `.heif` | JPEG bytes stay JPEG inside the PDF. Other rasters are lossless Flate. EXIF, 96 DPI, alpha onto white. A `.heic` name that is not HEIC is rejected. |
| SVG | `.svg` `.svgz` | CairoSVG (LibreOffice Draw if CairoSVG is missing). |
| Text | `.txt` `.md` | UTF-8 as A4 pages. Markdown is source text, not rendered. |
| Office | `.doc` `.docx` `.xls` `.xlsx` `.ppt` `.pptx` `.odt` `.ods` `.odp` `.rtf` | LibreOffice PDF when `soffice` is installed. Else `.docx`/`.xlsx`/`.pptx` text on A4. |

## API

- `POST /api/convert` — multipart field `file` (one or many)
- `GET /api/supported-types`
- `GET /healthz` · `GET /readyz`

```bash
curl -F 'file=@IMG_1234.JPG' http://localhost:8000/api/convert -o IMG_1234.pdf
```

## Tests

```bash
pytest
```

## Docker

```bash
docker build -t anythingintopdfbot:latest .
docker run --rm -p 8000:8000 \
  -e TELEGRAM_BOT_TOKEN \
  -e TELEGRAM_BOT_USERNAME \
  anythingintopdfbot:latest
```

## Deploy

When deployed, the UI and API share one host. Set `k8s/ingress.yaml` `spec.rules[0].host` and `k8s/kustomization.yaml` image name/tag.

```bash
kubectl apply -k k8s/
kubectl rollout status deployment/anythingintopdfbot -n anythingintopdfbot
```

Optional Telegram on the cluster (do not put the token in git):

```bash
kubectl -n anythingintopdfbot create secret generic anythingintopdfbot \
  --from-literal=TELEGRAM_BOT_TOKEN='YOUR_TOKEN' \
  --from-literal=TELEGRAM_BOT_USERNAME='YourBot'
```

The Deployment already reads that secret when it exists.

### GitHub Actions

Pushes to `main`, `master`, or `work` build `ghcr.io/YOUR_GITHUB_USERNAME/anythingintopdfbot`. Repository secret `KUBE_CONFIG` enables Kubernetes apply.

### Kuberns

Connect the GitHub repo; it uses `Procfile` + `requirements.txt`. Optional env: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`. Run command if asked:

```bash
gunicorn app.main:app --worker-class uvicorn.workers.UvicornWorker --workers 2 --bind 0.0.0.0:$PORT
```

# Regular-user convert flow

**Date:** 2026-08-13  
**Repo:** anythingintopdfbot (PNG-PDF)

## Intent

A person who finds this GitHub repo and runs the app is not attacking it. They open `/`, pick a normal file, click **Convert to PDF**, and save a PDF into Downloads. Coverage today is skewed toward clumsy/abuse cases (empty files, `.exe`, path-looking names). This spec is the **successful everyday session**.

## Persona

Alex cloned or opened the deployed site. They have a phone JPEG (`IMG_1234.JPG`), a macOS screenshot, a PDF they already have, and a short `notes.txt`. They convert those one at a time in the same browser tab. They never send HEIC, Office, or garbage bytes.

## Approaches

1. **Tests only** — new happy-path file, no product change. Fast, but the file picker still shows every file type.
2. **Tests + `accept` on the file input** (recommended) — OS picker prefers PNG/JPEG/PDF/TXT, matching the list on the page. One template attribute, generated from the same extension set the API uses.
3. **Tests + HTML error pages + multi-file + HEIC** — real product expansion. Out of scope; HEIC/Office stay unsupported.

Choose **2**. No new converters, no new dependencies.

## Design

**Tests** live in `tests/test_github_regular_user.py` only. They use FastAPI `TestClient` and Pillow-made files that look like real names/sizes. They do not duplicate `test_github_visitor_mistakes.py`.

Happy-path cases:

- Homepage copy still says convert + not persisted.
- File input `accept` lists the same extensions as `/api/supported-types` (comma-separated).
- `IMG_1234.JPG` (iPhone-style, uppercase) → 200 PDF, `Content-Disposition` filename `IMG_1234.pdf`, `attachment`.
- `Screenshot 2026-08-13 at 10.41.22 AM.png` → 200 PDF.
- `Holiday.jpeg` (Windows “JPEG” spelling) → 200 PDF.
- 800×600 photo → PDF `%PDF` + `%%EOF`; MediaBox is 96-DPI (600×450 pt), not 72-DPI poster math.
- Existing `Report.pdf` passthrough → download `Report.pdf`.
- Short English `notes.txt` → `notes.pdf`.
- One sitting: PNG, then JPG, then PDF, then TXT — all 200.

**Product change:** `app/templates/index.html` file input gets  
`accept="{{ supported_extensions|join(',') }}"`  
so the picker matches the list already rendered on the page.

## Out of scope

HEIC/Office conversion, multi-file select, HTML error pages, drag-drop JS, Telegram bot.

## Success

`pytest tests/test_github_regular_user.py` plus the existing suite stays green. A regular user converting a named JPEG sees `Name.pdf` in Downloads.

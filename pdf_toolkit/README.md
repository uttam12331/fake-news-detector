# PDF Toolkit

An iLovePDF-style PDF editor: merge, split, reorder/delete/extract pages,
rotate, password protect/unlock, watermark, image&harr;PDF conversion, and
compress-to-a-target-size. Installable as a PWA on Android/desktop.

## Layout

- `pdf_toolkit/` &mdash; the core library (no Flask dependency at this layer)
  - `merge.py`, `pages.py`, `protect.py`, `watermark.py`, `convert.py`, `compress.py`
  - `errors.py` &mdash; `PdfToolkitError` and subclasses raised on bad input
- `app/` &mdash; the Flask web app (`server.py`) + PWA frontend (`templates/`, `static/`)
- `tests/` &mdash; pytest suite for the core library

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest tests/ -q
python app/server.py
```

Then open `http://localhost:5050`.

## Install as an app (PWA)

This sandbox cannot compile a native Android APK (the Android SDK requires
downloading from Google's Maven repos, which are blocked by the network
policy here). Instead, the web app is a installable Progressive Web App:

1. Deploy/run the Flask app somewhere reachable over HTTPS (or `localhost`
   for local testing — Chrome treats `localhost` as a secure origin).
2. Open the site in Chrome on Android, or any desktop Chrome/Edge.
3. Use the browser's "Install app" / "Add to Home screen" prompt.

The app then runs full-screen with its own icon, and the service worker
caches the shell for fast repeat loads (page processing itself always needs
a live connection to the server).

## Compress-to-target-size

`pdf_toolkit.compress.compress(data, target_bytes=...)` recompresses every
raster image in the PDF, searching from least to most aggressive across
quality/downscale tiers, and returns the best (highest-quality) result that
still meets the target. If no tier reaches it, it returns the smallest
achieved result with `met_target=False`.

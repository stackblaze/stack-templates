# Automated template screenshots

Reliable, repeatable captures for ~200 Stackblaze templates — **1920×1080 viewport @ 2× device pixel ratio** (~3840×2160 PNG). Sharp enough for 1080p demo videos without upscaling blur.

## One-time setup

```bash
cd stack-templates/scripts
npm install
npm run capture:install   # downloads Chromium
```

## Single app

```bash
npm run capture -- --slug attendize --url https://witty-meadow-rpkq-9856.brave-harbor-fl5h-ead2.stackblaze.app

# Patch index.json + app.yaml screenshots
npm run capture -- --slug attendize --url https://... --apply
```

Output: `services/<slug>/screenshot-*.png`

## Batch (200 apps)

### Option A — QA cluster URLs (recommended)

Your platform already deploys templates for smoke tests and stores live URLs:

```bash
export STACKBLAZE_TOKEN='…'   # super-admin JWT or platform token
npm run capture:batch -- --qa --limit 20        # pilot
npm run capture:batch -- --qa --apply           # all passing QA deploys
```

Fetches `GET /api/platform/template-validation/status`, captures every `status: pass` with a URL.

### Option B — URL manifest

After deploying apps to your cluster, write `deploy-urls.json`:

```json
{
  "attendize": "https://witty-meadow-rpkq-9856.brave-harbor-fl5h-ead2.stackblaze.app",
  "metabase": "https://metabase-qa.example.stackblaze.app"
}
```

```bash
npm run capture:batch -- --manifest deploy-urls.json --apply
```

### Option C — URL template

```bash
npm run capture:batch -- \
  --slugs metabase,n8n,tandoor \
  --url-template 'https://{slug}-qa.stackblaze.app' \
  --apply
```

## Per-app capture specs

| File | Purpose |
|------|---------|
| `capture-specs/_default.json` | Homepage only — works for ~80% of apps |
| `capture-specs/<slug>.json` | Login flow + multiple pages |

### Spec example (login + pages)

```json
{
  "viewport": { "width": 1920, "height": 1080 },
  "deviceScaleFactor": 2,
  "login": {
    "path": "/login",
    "steps": [
      { "fill": { "input[name='email']": "admin@example.com" } },
      { "fill": { "input[name='password']": "changeme" } },
      { "click": "button[type='submit']" },
      { "waitForNavigation": true }
    ],
    "waitAfterMs": 2000
  },
  "pages": [
    { "name": "dashboard", "path": "/dashboard", "waitFor": ".main-content", "waitMs": 2000 },
    { "name": "settings", "path": "/settings", "waitMs": 1500 }
  ]
}
```

Add specs incrementally for apps that need auth or multi-page tours. Apps without a custom spec use `_default.json`.

## Recommended pipeline at scale

```
1. Queue QA deploys     →  POST /api/platform/template-validation/validate
2. Wait for pass        →  GET  .../status (url populated)
3. Seed demo data       →  per-app entrypoint/Job (like Attendize seeder)
4. Capture screenshots  →  npm run capture:batch -- --qa --apply
5. Commit PNGs + catalog → git push stack-templates main
6. Refresh API cache    →  POST .../refresh-catalog-cache
7. Render demo videos   →  hyperframes batch (separate step)
```

## Why not manual / hyperframes capture?

| Approach | Problem |
|----------|---------|
| Manual screenshots | 200 apps × 3–6 screens = not feasible |
| `hyperframes capture <vendor-url>` | Marketing site, not your deployment |
| HTTP scrape (`scrape-template-screenshots.py`) | og:image logos, not real UI |
| 1024px window grabs | Upscaled blur in 1080p video |

## Reports

Batch runs write `scripts/capture-report.json` with per-slug success/failure.

## Video generation (next step)

Screenshots from this tool feed directly into HyperFrames compositions (see `attendize-demo/`). A future `render-demo-batch.mjs` can loop `capture-specs` + `renders/` per slug.

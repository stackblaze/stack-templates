# Stackblaze Builder (catalog template)

Single Kubero app combining:

- **Web:** code-server + Node/pnpm/git (`Dockerfile` → `ghcr.io/stackblaze/stackblaze-builder`)
- **Add-on:** `KuberoSupabase` (self-hosted Supabase stack)
- **Volume:** `/home/coder/project` (10Gi) for the app being built

## Build & publish image

```bash
docker build -t ghcr.io/stackblaze/stackblaze-builder:latest .
docker push ghcr.io/stackblaze/stackblaze-builder:latest
```

Until the image is published, temporarily set `spec.image.repository` to `ghcr.io/coder/code-server` and tag `4.104.3` for smoke tests.

## Catalog index

After adding this service, append an entry to `index.json` (or run your catalog sync workflow) with `"dirname": "stackblaze-builder"` and `"addons": ["KuberoSupabase"]`.

## Kubero tier

Register in `kubero/server/src/templates/template-tiers.ts` as tier **4** (Very heavy) due to Supabase + CNPG footprint.

## Stackblaze Builder product

Deploy via `deploy_template` with template id `stackblaze-builder`, or let `WorkspaceService` create this app in the `_stackblaze-builder` pipeline. The workspace is a **persistent Kubero app** — PVC keeps `/home/coder/project` until the user deletes the app. See `docs/builder/APP-LIFECYCLE.md`.

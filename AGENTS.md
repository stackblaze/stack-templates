# AGENTS.md — stack-templates

## What this repo is

The StackBlaze template catalog (forked from `kubero-dev/templates`): `index.json`,
`index-frameworks.json` and one `services/<name>/app.yaml` per app (about 300).
There is no build step. kubero-server reads the catalog anonymously from
`raw.githubusercontent.com/stackblaze/stack-templates/main/...` (both
`helm-charts/kubero/values.yaml` and `values-dev.yaml` in kubero-server point at
`main`), so a merge to `main` is live for prod and api-dev on the next fetch.

## Build / test / lint

No package build and no CI runs on pull requests. Check templates locally with
the repo's scripts before committing (Python 3 + PyYAML):

```sh
python3 scripts/migrate-to-communal-db-env.py --check   # DB env contract lint, exit 1 on literal hosts/users/passwords
python3 scripts/lint-template-addons.py                 # fails on retired add-on kinds
python3 scripts/sync-index-addons.py                    # rewrites index.json `addons` from each app.yaml
python3 scripts/generate-qa-table.py                    # regenerates the README QA table from qa-status.json
```

As of 2026-10-15 the `--check` lint already reports 6 pre-existing failures on
`main`; do not add new ones.

Screenshot/demo tooling lives in `scripts/package.json` (`npm run capture`,
`capture:batch`, `capture:install`, `upload:video`, run from `scripts/`).

Workflows in `.github/workflows` (none gate PRs):

- `Build Hermes image`, `Build Medusa Kubero image`, `Build PrestaShop Kubero image`,
  `Build Stackblaze Workspace image` — on push to `main` touching that service's
  folder (or manual dispatch); push images to `ghcr.io/stackblaze/...`.
- `Mirror upstream dependencies to ghcr.io/stackblaze` (`mirror-deps.yaml`) —
  manual dispatch only; copies listed Docker Hub images to
  `ghcr.io/stackblaze/stack-templates/<name>:<same tag>`.

## Branch and ship flow

- Integration branch is `main`. The `dev` branch is retired (it has had no
  commits since 2026-09-27 and is far behind `main`); do not branch from or PR
  into it.
- Branch from the latest `main` as `<your-name>/<topic>`, open a PR into `main`.
- Merging to `main` is the release: there is no separate dev catalog, so it
  reaches every zone (prod and dev) at once. Agents never merge PRs into `main`
  and never open or merge any release/promotion to prod themselves; Adam merges.
- Changes to `services/hermes|medusa|prestashop|stackblaze-workspace/**` also
  trigger the image build workflows above on merge.

## House rules

- Never print or commit secrets; read secret files by key name only; never pipe
  secrets into a heredoc script.
- No production changes, deletions or teardowns without an explicit human OK
  (stop and ask). Removing a template from `index.json` or `services/` removes it
  from the live catalog.
- Commit as `adam@stackblaze.com` (current rule; Vercel rejects other authors for
  the dashboard). Add an `Agent: <name>` trailer to agent-made commits.
- Own branch (`<your-name>/<topic>`); never push to someone else's branch or
  force-push shared ones; rebase on the latest `main` before merge; nobody pushes
  to `main` directly.
- Announce in the team channel before (and after) using the shared dev
  environment (api-dev / dashboard-dev / dev zone `shared-dev-west-1-a`) to test a
  template; last deploy wins.
- Never create backup schedules unless the customer turned backups on: templates
  must not ship backup `Schedule` resources.

## Repo-specific gotchas

- **Communal DB contract** (README "Database connection contract"): never
  hard-code `{{KUBERO_APP_NAME}}-postgresql-rw`, `-mysql`, `rfr-...-valkey`, or a
  literal DB user/password; compose from injected `PGHOST`/`PGUSER`/...,
  `MYSQL_*`, `REDISHOST`/`REDISPORT`/`REDIS_URL` via `$(NAME)`. Never define a
  variable with an injected name, it overrides the real credentials. Keep the
  add-on CR (fallback on dedicated / non-communal zones).
- **Email add-on** (README "Email contract"): email variables go in the `Smtp`
  add-on entry's `env`, never in `spec.envVars`; then run `sync-index-addons.py`.
- **Images**: reference Docker Hub images as `docker.io/...` (zone nodes pull
  them through the regional zot mirror). `registry.stackblaze.cloud` is retired
  and returns 503 (commit 59507e5, #131); never point a template at it. Pin a
  tag, not `:latest` (see comments in `services/n8n`, `wordpress`, `focalboard`).
  The `mirror-deps` workflow is for Docker Hub 429 rate-limit cases only.
- **Shell-less images**: do not wrap a container in `/bin/sh -c` / `bash -c` or
  rely on `wget` unless the pinned image has them; mattermost crash-looped on a
  fresh pull for this (#33). Prefer the image's default entrypoint.
- **Runtime fetch from `main`**: some templates (e.g. n8n) download
  `services/<name>/kubero-entrypoint.sh` from raw `main` at container start, so
  editing it changes running apps on their next restart.
- **One template per app**: HA variants (`app.ha.yaml`) were removed 2026-09-02;
  do not add them. Template volumes are `storageClass: shared` + ReadWriteMany.
  `scripts/normalize-deployment-variants.py` predates this (writes HA variants
  and `lite` volumes); do not run it.
- **Index files**: there is no full regeneration script. Edit `index.json` /
  `index-frameworks.json` entries by hand and use `sync-index-addons.py` for the
  `addons` arrays; keep `template` URLs on `stackblaze/stack-templates/main`.

## Where work is tracked

- Handoff tracker: https://github.com/stackblaze/kubero-server/issues/1227
- GitHub issues labelled `handoff` (read the issue's Constraints section first)
- Wiki handover page: https://wiki.stackblaze.cloud/doc/developer-handover-ZRwIWfoPPv

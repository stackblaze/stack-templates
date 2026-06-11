# stack-templates

Kubero template catalog for the **stackblaze fork** of Kubero. Public so any
running Kubero in the stackblaze SaaS can fetch from `raw.githubusercontent.com`
anonymously.

Forked from upstream `kubero-dev/templates` + `kubero-dev/kubero/services/` and
consolidated into a single repo so the catalog has zero runtime dependency on
`kubero-dev/*`.

## Layout

- **`index.json`** — main catalog. Each entry's `template` field points at
  `services/<name>/app.yaml` in this repo.
- **`index-frameworks.json`** — frameworks catalog (2 entries).
- **`services/<name>/app.yaml`** — standard (minimal) deployment body Kubero
  pulls on install.
- **`services/<name>/app.ha.yaml`** — high-availability variant (when
  applicable). Listed in `index.json` under `deploymentTypes`.
- Icons are remote URLs in `index.json` (`icon`) and in each YAML
  (`kubero.dev/template.icon`); there is no separate build step.

## Standard vs high availability

Every template that needs a database or cache should use **Kubero addons**
(PostgreSQL, MariaDB, Valkey, ClickHouse, etc.) — even the **Standard**
variant. Standard does **not** mean “no database” or an embedded DB in the
app container.

| | Standard (`app.yaml`) | High availability (`app.ha.yaml`) |
|---|---|---|
| Addons | Yes — minimal topology | Same addon kinds, HA topology |
| PostgreSQL (CNPG) | `instances: 1` | `instances: 3` |
| MariaDB | `replicas: 1` | `replicas: 3` + Galera |
| Valkey | `arch: replica`, single shard | `arch: failover` + Sentinel |
| App `web.replicaCount` | Usually `1` | Usually `1` (HA is in the data layer) |

Catalog entries expose both via `deploymentTypes` in `index.json`:

- **`standard`** (default) — lower cost entry; single-node addons.
- **`ha`** — same app image and env; addons scaled for production resilience.

Users start on Standard and can move to HA when their plan allows (redeploy
with the HA deployment type or migrate the addon footprint). Do not put
Galera, multi-instance CNPG, or Valkey failover in `app.yaml`.

When adding a new template, always ship `app.yaml` + `app.ha.yaml` when the
app uses a stateful addon that supports clustering. Use
`scripts/generate-top10-templates.py` as a reference for addon helpers.

## Wiring Kubero to this catalog

Patch the Kubero CR (or the `kubero` ConfigMap) so the `templates.catalogs`
block references this repo:

```yaml
templates:
  enabled: true
  catalogs:
    - name: Kubero
      description: Kubero templates
      index:
        format: json
        url: https://raw.githubusercontent.com/stackblaze/stack-templates/main/index.json
      templateBasePath: https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/
    - name: Kubero Frameworks
      description: Kubero templates
      index:
        format: json
        url: https://raw.githubusercontent.com/stackblaze/stack-templates/main/index-frameworks.json
      templateBasePath: https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/
```

## Refreshing from upstream

When `kubero-dev/templates` adds a new service:

```sh
curl -fsSL https://raw.githubusercontent.com/kubero-dev/templates/main/index.json -o /tmp/index.json
curl -fsSL https://raw.githubusercontent.com/kubero-dev/templates/main/index-frameworks.json -o /tmp/index-frameworks.json
sed -i.bak 's|https://raw.githubusercontent.com/kubero-dev/kubero/main/services/|https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/|g' /tmp/index.json /tmp/index-frameworks.json
rm /tmp/*.bak
mv /tmp/index.json /tmp/index-frameworks.json ./
```

Then sync `services/` against `kubero-dev/kubero/services/` to pick up
any new template bodies the index references — `rsync -a --delete` works
if you have a clone of upstream.

## Local-only additions

Templates added in this fork that aren't upstream live alongside the
mirrored ones in `services/`. The refresh procedure above won't touch
them as long as their `dirname` doesn't collide with an upstream entry.

Current fork-only entries:
- `vikunja` — carried forward from the original stackblaze/kubero fork.
- `mattermost` — Team Edition (MIT) chat/collaboration server; not in upstream.
- `psono` — self-hosted password manager (combo CE); the six server keys are
  generated per-deploy via kubero `{{KUBERO_GEN_*}}` tokens.

## Editing template bodies

To replace cluster-specific defaults (e.g. swap a hard-coded
`storageClassName: standard` for the cluster's default), edit the
relevant `services/<name>/app.yaml` directly. No build step; the next
template install picks it up on the next fetch.

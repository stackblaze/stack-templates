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
- **`qa-status.json`** — QA pass overrides for the catalog table in this
  README (regenerate with `scripts/generate-qa-table.py`).
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

<!-- qa-table:start -->
## QA status

Whether each catalog template has been validated by QA on a live Kubero
cluster. **No** = not yet tested; **Yes** = QA verified; **—** = no HA
variant in the catalog.

To record a QA pass, edit `qa-status.json` and re-run
`python scripts/generate-qa-table.py`:

| App | Standard | HA |
|-----|:--------:|:---:|
| activepieces | No | No |
| affine | No | No |
| anse | No | — |
| appflowy | No | No |
| appsmith | No | — |
| archivebox | No | — |
| atuin | No | No |
| authorizer | No | — |
| azimutt | No | No |
| bitwarden | No | No |
| bluesky-pds | No | — |
| bookstack | No | No |
| calcom | No | No |
| casdoor | No | No |
| changedetection | No | — |
| chatpad | No | — |
| chatwoot | No | No |
| chibisafe | No | — |
| claper | No | No |
| cockpit | No | — |
| concrete5 | No | — |
| convertx | No | — |
| coral | No | — |
| corteza | No | No |
| cryptpad | No | No |
| dashy | No | — |
| databag | No | — |
| directus | No | — |
| discourse | No | No |
| doccano | No | — |
| docmost | No | No |
| documenso | No | No |
| docuseal | No | — |
| dokuwiki | No | — |
| dotcms | No | No |
| easyappointments | No | No |
| etherpad | No | No |
| evershop | No | No |
| excalidraw | No | — |
| fider | No | No |
| fief | No | — |
| filestash | No | — |
| flightlog | No | — |
| flowise | No | — |
| formbricks | No | No |
| freshrss | No | No |
| ghost | No | No |
| gitea | No | — |
| glpi | No | No |
| gotify | No | — |
| grav | No | — |
| guitos | No | — |
| hedgedoc | No | No |
| homarr | No | — |
| homebox | No | — |
| homer | No | — |
| humhub | No | No |
| illa | No | — |
| immich | No | No |
| infisical | No | No |
| jellyfin | No | No |
| joomla | No | No |
| kanboard | No | — |
| keila | No | No |
| kimai | No | No |
| kotaemon | No | — |
| kroki | No | No |
| kubectl | No | — |
| kuma | No | — |
| languagetool | No | — |
| leantime | No | No |
| libtranslate | No | — |
| limesurvey | No | No |
| linkwarden | No | No |
| logto | No | No |
| lychee | No | — |
| matomo | No | No |
| mattermost | No | No |
| mealie | No | No |
| memos | No | — |
| metabase | No | — |
| metube | No | — |
| microbin | No | — |
| mirotalk-p2p | No | — |
| moodist | No | — |
| mosparo | No | No |
| n8n | No | No |
| netbird | No | — |
| netbox | No | No |
| nextcloud | No | No |
| nocodb | No | — |
| nodebb | No | No |
| note-mark | No | — |
| ntfy | No | — |
| opengist | No | — |
| openproject | No | No |
| outline | No | No |
| pairdrop | No | — |
| paperless-ngx | No | No |
| paperless-ngx-sqlite | No | — |
| passbolt | No | No |
| password-pusher | No | No |
| penpot | No | No |
| penpot-backend | No | No |
| penpot-exporter | No | — |
| penpot-frontend | No | — |
| peppermint | No | No |
| photoview | No | No |
| piwigo | No | No |
| plane | No | No |
| planka | No | No |
| planning-poker | No | — |
| plausible | No | No |
| postiz | No | No |
| presentator | No | — |
| psono | No | No |
| rallly | No | No |
| raneto | No | — |
| rocketchat | No | — |
| rsshub | No | — |
| ryot | No | No |
| serge | No | — |
| serpbear | No | — |
| shiori | No | — |
| silverbullet | No | — |
| slash | No | — |
| slink | No | — |
| stirlingpdf | No | — |
| superset | No | No |
| syncthing | No | No |
| tasksmd | No | — |
| textbee | No | — |
| textbee-api | No | — |
| timetagger | No | — |
| tolgee | No | No |
| traggo | No | — |
| trilium | No | — |
| twenty | No | No |
| twofauth | No | — |
| typebot | No | No |
| umami | No | No |
| unleash | No | No |
| vaultwarden | No | — |
| vikunja | No | No |
| vvveb-mysql | No | No |
| wekan | No | — |
| whiteboard | No | — |
| wikijs | No | — |
| wordpress | No | No |
| workout-tracker | No | — |
| zipline | No | No |
| zulip | No | No |
<!-- qa-table:end -->

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

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
| Document DB (MongoDB-wire) | `nodeCount: 1` | `nodeCount: 3` |
| App `web.replicaCount` | Usually `1` | Usually `1` (HA is in the data layer) |

Use **Kubernetes operator add-ons** only — never deprecated `KuberoAddon*`
or `KuberoMongoDB`. All prerequisite operators (CNPG, MariaDB, Valkey,
Document DB, ClickHouse, Strimzi Kafka, RustFS, RabbitMQ, KubeDB Memcached,
Milvus, Weaviate, …) are installed via **`kubero-operator/operators/install.sh`**
into the cluster `operators` namespace. Every add-on block in templates must
use **`id: kubero-operator`** — the `kind` field selects the CR type
(`Cluster`, `MariaDB`, `DocumentDB`, `RabbitmqCluster`, etc.).

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
variant in the catalog. **Version** is the Docker image tag from
`services/<name>/app.yaml` (standard template). **Add-ons** lists Kubero
operator add-ons (`displayName` in each template) — databases, caches, and
queues are never embedded in the app container.

To record a QA pass, edit `qa-status.json` and re-run
`python scripts/generate-qa-table.py`:

<!-- Markdown tables do not span the README width; HTML table below. -->
<table width="100%">
  <thead>
    <tr>
      <th align="left" width="40"></th>
      <th align="left">App</th>
      <th align="center" width="100">Version</th>
      <th align="left">Add-ons</th>
      <th align="center" width="90">Standard</th>
      <th align="center" width="70">HA</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/99494700?s=200&amp;v=4" width="32" height="32" alt="activepieces" title="activepieces" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>activepieces</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/toeverything/AFFiNE/master/packages/frontend/admin/src/modules/auth/logo.svg" width="32" height="32" alt="affine" title="affine" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>affine</strong></td>
      <td align="center"><code>stable</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/anse-app/anse/refs/heads/main/public/pwa-192.png" width="32" height="32" alt="anse" title="anse" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>anse</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/86002201?s=200&amp;v=4" width="32" height="32" alt="appflowy" title="appflowy" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>appflowy</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey, RustFS</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/67620218?s=200&amp;v=4" width="32" height="32" alt="appsmith" title="appsmith" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>appsmith</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/74894248" width="32" height="32" alt="archivebox" title="archivebox" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>archivebox</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/122059230?s=200&amp;v=4" width="32" height="32" alt="atuin" title="atuin" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>atuin</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://authorizer.dev/images/favicon_io/android-chrome-192x192.png" width="32" height="32" alt="authorizer" title="authorizer" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>authorizer</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/89384563" width="32" height="32" alt="azimutt" title="azimutt" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>azimutt</strong></td>
      <td align="center"><code>—</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/15990069?s=200&amp;v=4" width="32" height="32" alt="bitwarden" title="bitwarden" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>bitwarden</strong></td>
      <td align="center"><code>beta</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/94650532?s=200&amp;v=4" width="32" height="32" alt="bluesky-pds" title="bluesky-pds" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>bluesky-pds</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/20912696?s=200&amp;v=4" width="32" height="32" alt="bookstack" title="bookstack" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>bookstack</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/79145102?s=200&amp;v=4" width="32" height="32" alt="calcom" title="calcom" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>calcom</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/72992104?s=200&amp;v=4" width="32" height="32" alt="casdoor" title="casdoor" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>casdoor</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://changedetection.io/themes/cdio/assets/images/favicons/apple-touch-icon.png" width="32" height="32" alt="changedetection" title="changedetection" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>changedetection</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/deiucanta/chatpad/refs/heads/main/src/assets/favicon.png" width="32" height="32" alt="chatpad" title="chatpad" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>chatpad</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/23416667?s=200&amp;v=4" width="32" height="32" alt="chatwoot" title="chatwoot" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>chatwoot</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/115422728?s=200&amp;v=4" width="32" height="32" alt="chibisafe" title="chibisafe" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>chibisafe</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/109804388?s=48&amp;v=4" width="32" height="32" alt="claper" title="claper" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>claper</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/78603032" width="32" height="32" alt="cockpit" title="cockpit" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>cockpit</strong></td>
      <td align="center"><code>core-latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/657929" width="32" height="32" alt="concrete5" title="concrete5" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>concrete5</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/18604702" width="32" height="32" alt="convertx" title="convertx" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>convertx</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/9255912?s=200&amp;v=4" width="32" height="32" alt="coral" title="coral" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>coral</strong></td>
      <td align="center"><code>7</code></td>
      <td>Valkey, Document DB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/50577806" width="32" height="32" alt="corteza" title="corteza" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>corteza</strong></td>
      <td align="center"><code>2023.3</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/76949612?s=200&amp;v=4" width="32" height="32" alt="cryptpad" title="cryptpad" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>cryptpad</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://i.ibb.co/yhbt6CY/dashy.png" width="32" height="32" alt="dashy" title="dashy" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>dashy</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/balzack/databag/main/doc/icon_v2.png" width="32" height="32" alt="databag" title="databag" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>databag</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/15967950" width="32" height="32" alt="directus" title="directus" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>directus</strong></td>
      <td align="center"><code>11</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/3220138?s=200&amp;v=4" width="32" height="32" alt="discourse" title="discourse" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>discourse</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/58067660" width="32" height="32" alt="doccano" title="doccano" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>doccano</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/150462874" width="32" height="32" alt="docmost" title="docmost" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>docmost</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/127681099" width="32" height="32" alt="documenso" title="documenso" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>documenso</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/138379721" width="32" height="32" alt="docuseal" title="docuseal" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>docuseal</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/111377700" width="32" height="32" alt="dokuwiki" title="dokuwiki" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>dokuwiki</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/1005263?s=200&amp;v=4" width="32" height="32" alt="dotcms" title="dotcms" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>dotcms</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), OpenSearch</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/4527441?s=200&amp;v=4" width="32" height="32" alt="easyappointments" title="easyappointments" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>easyappointments</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/181731?s=200&amp;v=4" width="32" height="32" alt="etherpad" title="etherpad" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>etherpad</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/83757778?s=200&amp;v=4" width="32" height="32" alt="evershop" title="evershop" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>evershop</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/59452120?s=200&amp;v=4" width="32" height="32" alt="excalidraw" title="excalidraw" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>excalidraw</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/25187431" width="32" height="32" alt="fider" title="fider" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>fider</strong></td>
      <td align="center"><code>stable</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/97037414?s=200&amp;v=4" width="32" height="32" alt="fief" title="fief" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>fief</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/mickael-kerjean/filestash/refs/heads/master/public/assets/logo/favicon.svg" width="32" height="32" alt="filestash" title="filestash" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>filestash</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/4271779" width="32" height="32" alt="flightlog" title="flightlog" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>flightlog</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/128289781?s=200&amp;v=4" width="32" height="32" alt="flowise" title="flowise" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>flowise</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/105877416?s=200&amp;v=4" width="32" height="32" alt="formbricks" title="formbricks" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>formbricks</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/9414285?s=200&amp;v=4" width="32" height="32" alt="freshrss" title="freshrss" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>freshrss</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://ghost.org/images/logos/ghost-logo-orb.png" width="32" height="32" alt="ghost" title="ghost" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>ghost</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/12724356?s=200&amp;v=4" width="32" height="32" alt="gitea" title="gitea" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>gitea</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/13361707?s=200&amp;v=4" width="32" height="32" alt="glpi" title="glpi" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>glpi</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/gotify/logo/master/gotify-logo.png" width="32" height="32" alt="gotify" title="gotify" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>gotify</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/8237355" width="32" height="32" alt="grav" title="grav" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>grav</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/5001560" width="32" height="32" alt="guitos" title="guitos" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>guitos</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/67865462?s=200&amp;v=4" width="32" height="32" alt="hedgedoc" title="hedgedoc" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>hedgedoc</strong></td>
      <td align="center"><code>1.10.8</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://github.com/ajnart/homarr/raw/dev/public/imgs/logo/logo-color.svg" width="32" height="32" alt="homarr" title="homarr" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>homarr</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://homebox.software/lilbox.svg" width="32" height="32" alt="homebox" title="homebox" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>homebox</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/bastienwirtz/homer/main/public/logo.png" width="32" height="32" alt="homer" title="homer" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>homer</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/6262639?s=200&amp;v=4" width="32" height="32" alt="humhub" title="humhub" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>humhub</strong></td>
      <td align="center"><code>stable</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/93245159?s=200&amp;v=4" width="32" height="32" alt="illa" title="illa" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>illa</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/109746326?s=200&amp;v=4" width="32" height="32" alt="immich" title="immich" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>immich</strong></td>
      <td align="center"><code>release</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/107880645?s=200&amp;v=4" width="32" height="32" alt="infisical" title="infisical" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>infisical</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/45698031?s=200&amp;v=4" width="32" height="32" alt="jellyfin" title="jellyfin" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>jellyfin</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/751633?s=200&amp;v=4" width="32" height="32" alt="joomla" title="joomla" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>joomla</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/13722943?s=200&amp;v=4" width="32" height="32" alt="kanboard" title="kanboard" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>kanboard</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/pentacent/keila/main/.github/assets/logo.svg" width="32" height="32" alt="keila" title="keila" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>keila</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Haraka Mail Server</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/981996" width="32" height="32" alt="kimai" title="kimai" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>kimai</strong></td>
      <td align="center"><code>apache</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/3265185" width="32" height="32" alt="kotaemon" title="kotaemon" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>kotaemon</strong></td>
      <td align="center"><code>main-full</code></td>
      <td>Milvus</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/4894788?s=200&amp;v=4" width="32" height="32" alt="kroki" title="kroki" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>kroki</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/52770786?s=200&amp;v=4" width="32" height="32" alt="kubectl" title="kubectl" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>kubectl</strong></td>
      <td align="center"><code>—</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://github.com/louislam/uptime-kuma/raw/master/public/icon.svg" width="32" height="32" alt="kuma" title="kuma" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>kuma</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/5187764?s=200&amp;v=4" width="32" height="32" alt="languagetool" title="languagetool" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>languagetool</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/11252321?s=200&amp;v=4" width="32" height="32" alt="leantime" title="leantime" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>leantime</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/77352747" width="32" height="32" alt="libtranslate" title="libtranslate" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>libtranslate</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/1364105?s=200&amp;v=4" width="32" height="32" alt="limesurvey" title="limesurvey" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>limesurvey</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/135248736?s=200&amp;v=4" width="32" height="32" alt="linkwarden" title="linkwarden" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>linkwarden</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/84981374" width="32" height="32" alt="logto" title="logto" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>logto</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/37916028?s=200&amp;v=4" width="32" height="32" alt="lychee" title="lychee" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>lychee</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/698038?s=200&amp;v=4" width="32" height="32" alt="matomo" title="matomo" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>matomo</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/9828093?s=200&amp;v=4" width="32" height="32" alt="mattermost" title="mattermost" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>mattermost</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/92342333?s=200&amp;v=4" width="32" height="32" alt="mealie" title="mealie" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>mealie</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/95764151?s=200&amp;v=4" width="32" height="32" alt="memos" title="memos" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>memos</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/10520629" width="32" height="32" alt="metabase" title="metabase" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>metabase</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/alexta69/metube/master/ui/src/assets/icons/android-chrome-192x192.png" width="32" height="32" alt="metube" title="metube" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>metube</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/szabodanika/microbin/refs/heads/master/templates/assets/logo-square.png" width="32" height="32" alt="microbin" title="microbin" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>microbin</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://www.saashub.com/images/app/service_logos/213/pgzsasbgu5fr/large.png?1653219756" width="32" height="32" alt="mirotalk-p2p" title="mirotalk-p2p" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>mirotalk-p2p</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://moodist.mvze.net/favicon.svg" width="32" height="32" alt="moodist" title="moodist" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>moodist</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/83111146?s=200&amp;v=4" width="32" height="32" alt="mosparo" title="mosparo" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>mosparo</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/45487711?s=200&amp;v=4" width="32" height="32" alt="n8n" title="n8n" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>n8n</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/100464677" width="32" height="32" alt="netbird" title="netbird" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>netbird</strong></td>
      <td align="center"><code>main</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/44905828?s=200&amp;v=4" width="32" height="32" alt="netbox" title="netbox" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>netbox</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/19211038?s=200&amp;v=4" width="32" height="32" alt="nextcloud" title="nextcloud" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>nextcloud</strong></td>
      <td align="center"><code>apache</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/nocodb/nocodb/develop/packages/nc-gui/assets/img/icons/512x512.png" width="32" height="32" alt="nocodb" title="nocodb" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>nocodb</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/4449608?s=200&amp;v=4" width="32" height="32" alt="nodebb" title="nodebb" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>nodebb</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/enchant97/note-mark/refs/heads/main/frontend/public/icon.svg" width="32" height="32" alt="note-mark" title="note-mark" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>note-mark</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://ntfy.sh/_next/static/media/logo.077f6a13.svg" width="32" height="32" alt="ntfy" title="ntfy" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>ntfy</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/thomiceli/opengist/master/public/opengist.svg" width="32" height="32" alt="opengist" title="opengist" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>opengist</strong></td>
      <td align="center"><code>1</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/1756674?s=200&amp;v=4" width="32" height="32" alt="openproject" title="openproject" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>openproject</strong></td>
      <td align="center"><code>16-slim</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/1765001" width="32" height="32" alt="outline" title="outline" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>outline</strong></td>
      <td align="center"><code>latest</code></td>
      <td>Valkey, PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/52242352" width="32" height="32" alt="pairdrop" title="pairdrop" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>pairdrop</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/99562962" width="32" height="32" alt="paperless-ngx" title="paperless-ngx" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>paperless-ngx</strong></td>
      <td align="center"><code>latest</code></td>
      <td>Valkey, PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/99562962" width="32" height="32" alt="paperless-ngx-sqlite" title="paperless-ngx-sqlite" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>paperless-ngx-sqlite</strong></td>
      <td align="center"><code>latest</code></td>
      <td>Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/4386228?s=200&amp;v=4" width="32" height="32" alt="passbolt" title="passbolt" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>passbolt</strong></td>
      <td align="center"><code>latest-ce</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/395132?s=200&amp;v=4" width="32" height="32" alt="password-pusher" title="password-pusher" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>password-pusher</strong></td>
      <td align="center"><code>stable</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/30179644?s=200&amp;v=4" width="32" height="32" alt="penpot" title="penpot" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>penpot</strong></td>
      <td align="center"><code>—</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/30179644" width="32" height="32" alt="penpot-backend" title="penpot-backend" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>penpot-backend</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/30179644" width="32" height="32" alt="penpot-exporter" title="penpot-exporter" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>penpot-exporter</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/30179644" width="32" height="32" alt="penpot-frontend" title="penpot-frontend" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>penpot-frontend</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/76014454" width="32" height="32" alt="peppermint" title="peppermint" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>peppermint</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/75802894?s=200&amp;v=4" width="32" height="32" alt="photoview" title="photoview" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>photoview</strong></td>
      <td align="center"><code>2</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/9326886" width="32" height="32" alt="piwigo" title="piwigo" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>piwigo</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/115727700?s=200&amp;v=4" width="32" height="32" alt="plane" title="plane" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>plane</strong></td>
      <td align="center"><code>stable</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/64215741?s=200&amp;v=4" width="32" height="32" alt="planka" title="planka" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>planka</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/axeleroy/self-host-planning-poker/main/assets/icon.svg" width="32" height="32" alt="planning-poker" title="planning-poker" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>planning-poker</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/54802774?s=200&amp;v=4" width="32" height="32" alt="plausible" title="plausible" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>plausible</strong></td>
      <td align="center"><code>v3.0.1</code></td>
      <td>PostgreSQL (CloudNativePG), ClickHouse</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/gitroomhq/postiz-app/21eae29b52456cb98ba1b8dcd3ed504e344c0bec/apps/frontend/public/postiz.svg" width="32" height="32" alt="postiz" title="postiz" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>postiz</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/53578609" width="32" height="32" alt="presentator" title="presentator" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>presentator</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/29746989?s=200&amp;v=4" width="32" height="32" alt="psono" title="psono" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>psono</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://rallly.co/favicon-196x196.png" width="32" height="32" alt="rallly" title="rallly" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>rallly</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/gilbitron/Raneto/master/logo/logo_readme.png" width="32" height="32" alt="raneto" title="raneto" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>raneto</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/12508788?s=200&amp;v=4" width="32" height="32" alt="rocketchat" title="rocketchat" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>rocketchat</strong></td>
      <td align="center"><code>latest</code></td>
      <td>Document DB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/DIYgod/RSSHub/master/lib/assets/logo.png" width="32" height="32" alt="rsshub" title="rsshub" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>rsshub</strong></td>
      <td align="center"><code>chromium-bundled</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/60938164?v=4" width="32" height="32" alt="ryot" title="ryot" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>ryot</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/135821135?s=200&amp;v=4" width="32" height="32" alt="serge" title="serge" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>serge</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/towfiqi/serpbear/refs/heads/main/public/icon.png" width="32" height="32" alt="serpbear" title="serpbear" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>serpbear</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/go-shiori/shiori/master/internal/view/assets/res/apple-touch-icon-152x152.png" width="32" height="32" alt="shiori" title="shiori" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>shiori</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/108344757" width="32" height="32" alt="silverbullet" title="silverbullet" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>silverbullet</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/140182318" width="32" height="32" alt="slash" title="slash" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>slash</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/andrii-kryvoviaz/slink/refs/heads/main/services/client/static/favicon.png" width="32" height="32" alt="slink" title="slink" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>slink</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/Frooodle/Stirling-PDF/main/docs/stirling.png" width="32" height="32" alt="stirlingpdf" title="stirlingpdf" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>stirlingpdf</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/47359?s=200&amp;v=4" width="32" height="32" alt="superset" title="superset" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>superset</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/7628018?s=200&amp;v=4" width="32" height="32" alt="syncthing" title="syncthing" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>syncthing</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/BaldissaraMatheus/Tasks.md/main/frontend/public/favicon/android-chrome-192x192.png" width="32" height="32" alt="tasksmd" title="tasksmd" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>tasksmd</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/38871878" width="32" height="32" alt="textbee" title="textbee" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>textbee</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/38871878" width="32" height="32" alt="textbee-api" title="textbee-api" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>textbee-api</strong></td>
      <td align="center"><code>latest</code></td>
      <td>Document DB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://timetagger.app/timetagger_sl.svg" width="32" height="32" alt="timetagger" title="timetagger" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>timetagger</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/78480209" width="32" height="32" alt="tolgee" title="tolgee" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>tolgee</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/traggo/logo/master/logo.png" width="32" height="32" alt="traggo" title="traggo" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>traggo</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/160046342" width="32" height="32" alt="trilium" title="trilium" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>trilium</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/119600397" width="32" height="32" alt="twenty" title="twenty" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>twenty</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://docs.2fauth.app/static/2fauth_dark.png" width="32" height="32" alt="twofauth" title="twofauth" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>twofauth</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/16015833?s=200&amp;v=4" width="32" height="32" alt="typebot" title="typebot" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>typebot</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/105618662?s=200&amp;v=4" width="32" height="32" alt="umami" title="umami" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>umami</strong></td>
      <td align="center"><code>postgresql-latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/23053233?s=200&amp;v=4" width="32" height="32" alt="unleash" title="unleash" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>unleash</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/dani-garcia/vaultwarden/main/resources/vaultwarden-icon.svg" width="32" height="32" alt="vaultwarden" title="vaultwarden" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>vaultwarden</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/41270016?s=200&amp;v=4" width="32" height="32" alt="vikunja" title="vikunja" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>vikunja</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://camo.githubusercontent.com/d9af82329f3a4ace7ba38d2c21120fadbdd77059bc91abdb32e0a4bdb93a0a38/68747470733a2f2f76767665622e636f6d2f61646d696e2f64656661756c742f696d672f6269676c6f676f2e706e67" width="32" height="32" alt="vvveb-mysql" title="vvveb-mysql" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>vvveb-mysql</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/11725037" width="32" height="32" alt="wekan" title="wekan" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>wekan</strong></td>
      <td align="center"><code>latest</code></td>
      <td>Document DB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://static-00.iconduck.com/assets.00/whiteboard-icon-512x416-i0xojg3v.png" width="32" height="32" alt="whiteboard" title="whiteboard" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>whiteboard</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/requarks/wiki/main/client/static/favicons/android-chrome-256x256.png" width="32" height="32" alt="wikijs" title="wikijs" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>wikijs</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/276006?s=280" width="32" height="32" alt="wordpress" title="wordpress" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>wordpress</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://github.com/cristianmarint/MotionGym/raw/master/docs/imgs/logo.png" width="32" height="32" alt="workout-tracker" title="workout-tracker" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>workout-tracker</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/1396645" width="32" height="32" alt="zipline" title="zipline" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>zipline</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/4921959?s=200&amp;v=4" width="32" height="32" alt="zulip" title="zulip" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>zulip</strong></td>
      <td align="center"><code>10.2-1</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey, RabbitMQ, Memcached</td>
      <td align="center">No</td>
      <td align="center">No</td>
    </tr>
  </tbody>
</table>
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

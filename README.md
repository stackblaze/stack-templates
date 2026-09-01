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

## One template per app (HA variants removed)

The catalog used to ship `app.yaml` + `app.ha.yaml` per service. The HA
variant was removed on 2026-09-02: on the shared tier the platform itself
provides the resilience the variant used to encode — databases are logical
instances on the zone's communal servers (CNPG ×3 / MariaDB primary+replica),
the platform pins app volumes to the RWX `shared` class where it exists, and
web replicas are scalable from the dashboard. Do not add `app.ha.yaml` or
Galera/multi-instance topology to new templates; a per-cluster scale knob is
the plan for dedicated deployments.

## Database connection contract (communal databases)

On shared zones the platform provisions Postgres and MariaDB add-ons as
**logical databases on the zone's communal server** (one role + database per
add-on, random password, a stateless pooler pod + a Service named after the
add-on instance in the tenant namespace) and Valkey as an ephemeral instance.
The add-on CR in the template is still what gets created on zones without a
communal server and on dedicated clusters — keep it — but **nothing in the
template may assume the CR's host name, user, database or password**: in
logical mode those are `<namespace>_<instance>`, a minted password, and the
`<instance>` Service.

Instead, kubero-server injects the connection contract into every app that
references the add-on, and templates compose their own variables from it with
Kubernetes `$(NAME)` expansion (kubero-server dependency-orders the env list):

| Add-on kind | Injected variables |
|---|---|
| `Cluster` (CloudNativePG) | `PGHOST` `PGPORT` `PGUSER` `PGDATABASE` `PGPASSWORD` |
| `MariaDB` | `MYSQL_HOST` `MYSQL_PORT` `MYSQL_USER` `MYSQL_DATABASE` `MYSQL_PASSWORD` |
| `Valkey` | `REDISHOST` `REDISPORT` `REDIS_URL` |

```yaml
envVars:
- name: DATABASE_URL
  value: 'postgresql://$(PGUSER):$(PGPASSWORD)@$(PGHOST):$(PGPORT)/$(PGDATABASE)?sslmode=disable'
- name: DB_HOST
  value: '$(MYSQL_HOST)'
- name: DB_PASSWORD
  value: '$(MYSQL_PASSWORD)'
- name: REDIS_URL
  value: 'redis://$(REDISHOST):$(REDISPORT)/0'
```

Rules:

- Never write `{{KUBERO_APP_NAME}}-postgresql-rw`, `{{KUBERO_APP_NAME}}-mysql`,
  `rfr-{{KUBERO_APP_NAME}}-valkey-readwrite`, or a literal user/database/
  password into `envVars`. Reference the injected variable.
- Never define a variable **named** like an injected one (`PGPASSWORD`,
  `MYSQL_HOST`, …) in a template — an explicit template value wins over the
  injection and blocks the real credentials.
- `bootstrap.initdb.postInitApplicationSQL` in the CNPG CR only runs in
  server mode. In logical mode the tenant role owns its database (it can
  `CREATE EXTENSION` any *trusted* extension itself); a template that needs a
  superuser-only extension (`vector`), a second database, `CREATE DATABASE`
  rights or MariaDB `root` cannot run logically — see the compatibility list in
  `docs3.0/communal-databases.md`.
- `scripts/migrate-to-communal-db-env.py --check` lints every DB-backed
  template against this contract (run it before committing; it is also the
  tool that performed the catalog-wide rewrite).

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
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/activepieces/icon.png" width="32" height="32" alt="activepieces" title="activepieces" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>activepieces</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/actual-budget/icon.png" width="32" height="32" alt="actual-budget" title="actual-budget" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>actual-budget</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/adminer/icon.png" width="32" height="32" alt="adminer" title="adminer" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>adminer</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/affine/icon.png" width="32" height="32" alt="affine" title="affine" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>affine</strong></td>
      <td align="center"><code>stable</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://airflow.apache.org/images/airflow-logo-padded.svg" width="32" height="32" alt="airflow" title="airflow" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>airflow</strong></td>
      <td align="center"><code>2.10.5-python3.12</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/akaunting/icon.png" width="32" height="32" alt="akaunting" title="akaunting" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>akaunting</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/anythingllm/icon.png" width="32" height="32" alt="anythingllm" title="anythingllm" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>anythingllm</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/appflowy/icon.png" width="32" height="32" alt="appflowy" title="appflowy" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>appflowy</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey, RustFS</td>
      <td align="center">No</td>
      <td align="center">—</td>
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
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/archivebox/icon.png" width="32" height="32" alt="archivebox" title="archivebox" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>archivebox</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/attendize/icon.png" width="32" height="32" alt="attendize" title="attendize" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>attendize</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB, Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/122059230?s=200&amp;v=4" width="32" height="32" alt="atuin" title="atuin" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>atuin</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/88282323?s=200&amp;v=4" width="32" height="32" alt="audiobookshelf" title="audiobookshelf" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>audiobookshelf</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/authelia/icon.png" width="32" height="32" alt="authelia" title="authelia" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>authelia</strong></td>
      <td align="center"><code>4.39</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/authentik/icon.png" width="32" height="32" alt="authentik" title="authentik" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>authentik</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://authorizer.dev/images/favicon_io/android-chrome-192x192.png" width="32" height="32" alt="authorizer" title="authorizer" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>authorizer</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/automatisch/icon.png" width="32" height="32" alt="automatisch" title="automatisch" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>automatisch</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/89384563" width="32" height="32" alt="azimutt" title="azimutt" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>azimutt</strong></td>
      <td align="center"><code>main</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/azuracast/icon.png" width="32" height="32" alt="azuracast" title="azuracast" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>azuracast</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB, Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/baserow/icon.png" width="32" height="32" alt="baserow" title="baserow" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>baserow</strong></td>
      <td align="center"><code>2.2.2</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/bigcapital/icon.png" width="32" height="32" alt="bigcapital" title="bigcapital" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>bigcapital</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB, Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/15990069?s=200&amp;v=4" width="32" height="32" alt="bitwarden" title="bitwarden" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>bitwarden</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/bookstack/icon.png" width="32" height="32" alt="bookstack" title="bookstack" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>bookstack</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/btcpay/icon.png" width="32" height="32" alt="btcpay" title="btcpay" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>btcpay</strong></td>
      <td align="center"><code>2.3.9</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/calcom/icon.png" width="32" height="32" alt="calcom" title="calcom" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>calcom</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/18373368?s=200&amp;v=4" width="32" height="32" alt="calibre-web" title="calibre-web" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>calibre-web</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/72992104?s=200&amp;v=4" width="32" height="32" alt="casdoor" title="casdoor" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>casdoor</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/castopod/icon.png" width="32" height="32" alt="castopod" title="castopod" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>castopod</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB, Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/changedetection/icon.png" width="32" height="32" alt="changedetection" title="changedetection" style="vertical-align:middle;border-radius:4px;" /></td>
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
      <td><img src="https://cdn.jsdelivr.net/gh/stackblaze/stack-templates@59942969b534f4de6df6313e53a02b7222202457/services/chatwoot/icon.png" width="32" height="32" alt="chatwoot" title="chatwoot" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>chatwoot</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
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
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/chiefonboarding/icon.png" width="32" height="32" alt="chiefonboarding" title="chiefonboarding" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>chiefonboarding</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/civicrm/icon.png" width="32" height="32" alt="civicrm" title="civicrm" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>civicrm</strong></td>
      <td align="center"><code>5</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/109804388?s=48&amp;v=4" width="32" height="32" alt="claper" title="claper" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>claper</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/clickhouse/icon.png" width="32" height="32" alt="clickhouse" title="clickhouse" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>clickhouse</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
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
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/convex/icon.png" width="32" height="32" alt="convex" title="convex" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>convex</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/corteza/icon.png" width="32" height="32" alt="corteza" title="corteza" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>corteza</strong></td>
      <td align="center"><code>2023.3</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/countly/icon.png" width="32" height="32" alt="countly" title="countly" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>countly</strong></td>
      <td align="center"><code>23.11.22</code></td>
      <td>Document DB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/crater/icon.png" width="32" height="32" alt="crater" title="crater" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>crater</strong></td>
      <td align="center"><code>php7.4</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/cryptgeon/icon.png" width="32" height="32" alt="cryptgeon" title="cryptgeon" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>cryptgeon</strong></td>
      <td align="center"><code>latest</code></td>
      <td>Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/cryptomator/icon.png" width="32" height="32" alt="cryptomator" title="cryptomator" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>cryptomator</strong></td>
      <td align="center"><code>stable</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/cryptpad/icon.png" width="32" height="32" alt="cryptpad" title="cryptpad" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>cryptpad</strong></td>
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
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://cdn.jsdelivr.net/gh/stackblaze/stack-templates@e63cc2a96db49c9abb60cb62e0a6b20b6ad3346f/services/discourse/icon.png" width="32" height="32" alt="discourse" title="discourse" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>discourse</strong></td>
      <td align="center"><code>3-debian-12</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/dittofeed/icon.png" width="32" height="32" alt="dittofeed" title="dittofeed" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>dittofeed</strong></td>
      <td align="center"><code>v0.23.0</code></td>
      <td>PostgreSQL (CloudNativePG), ClickHouse</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/docassemble/icon.png" width="32" height="32" alt="docassemble" title="docassemble" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>docassemble</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/58067660" width="32" height="32" alt="doccano" title="doccano" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>doccano</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/docmost/icon.png" width="32" height="32" alt="docmost" title="docmost" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>docmost</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/docspell/icon.png" width="32" height="32" alt="docspell" title="docspell" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>docspell</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/127681099" width="32" height="32" alt="documenso" title="documenso" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>documenso</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/documize/icon.png" width="32" height="32" alt="documize" title="documize" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>documize</strong></td>
      <td align="center"><code>bookworm-slim</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/docuseal/icon.png" width="32" height="32" alt="docuseal" title="docuseal" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>docuseal</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
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
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/dolibarr/icon.png" width="32" height="32" alt="dolibarr" title="dolibarr" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>dolibarr</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/1005263?s=200&amp;v=4" width="32" height="32" alt="dotcms" title="dotcms" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>dotcms</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), OpenSearch</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/drawio/icon.png" width="32" height="32" alt="drawio" title="drawio" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>drawio</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/dremio/icon.png" width="32" height="32" alt="dremio" title="dremio" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>dremio</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/drupal/icon.png" width="32" height="32" alt="drupal" title="drupal" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>drupal</strong></td>
      <td align="center"><code>10-apache</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/easyappointments/icon.png" width="32" height="32" alt="easyappointments" title="easyappointments" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>easyappointments</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/element/icon.png" width="32" height="32" alt="element" title="element" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>element</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/emqx/icon.png" width="32" height="32" alt="emqx" title="emqx" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>emqx</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/eneo/icon.png" width="32" height="32" alt="eneo" title="eneo" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>eneo</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/erpnext/icon.png" width="32" height="32" alt="erpnext" title="erpnext" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>erpnext</strong></td>
      <td align="center"><code>version-15</code></td>
      <td>MariaDB, Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/erugo/icon.png" width="32" height="32" alt="erugo" title="erugo" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>erugo</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/8108711?s=200&amp;v=4" width="32" height="32" alt="espocrm" title="espocrm" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>espocrm</strong></td>
      <td align="center"><code>apache</code></td>
      <td>MariaDB, Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/etherpad/icon.png" width="32" height="32" alt="etherpad" title="etherpad" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>etherpad</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/83757778?s=200&amp;v=4" width="32" height="32" alt="evershop" title="evershop" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>evershop</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/excalidraw/icon.png" width="32" height="32" alt="excalidraw" title="excalidraw" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>excalidraw</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/fider/icon.png" width="32" height="32" alt="fider" title="fider" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>fider</strong></td>
      <td align="center"><code>stable</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/97037414?s=200&amp;v=4" width="32" height="32" alt="fief" title="fief" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>fief</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/35781395?v=4" width="32" height="32" alt="filebrowser" title="filebrowser" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>filebrowser</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/filestash/icon.png" width="32" height="32" alt="filestash" title="filestash" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>filestash</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/firefly-iii/icon.png" width="32" height="32" alt="firefly-iii" title="firefly-iii" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>firefly-iii</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB, Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/flarum/icon.png" width="32" height="32" alt="flarum" title="flarum" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>flarum</strong></td>
      <td align="center"><code>stable</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/flatnotes/icon.png" width="32" height="32" alt="flatnotes" title="flatnotes" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>flatnotes</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://cdn.jsdelivr.net/gh/stackblaze/stack-templates@83ba43b1da8347f3a7af802fb213a0e2ca9a37bb/services/flowise/icon.png" width="32" height="32" alt="flowise" title="flowise" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>flowise</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/focalboard/icon.png" width="32" height="32" alt="focalboard" title="focalboard" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>focalboard</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://codeberg.org/forgejo/Forgejo/raw/branch/forgejo/public/assets/img/logo.svg" width="32" height="32" alt="forgejo" title="forgejo" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>forgejo</strong></td>
      <td align="center"><code>11</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/formbricks/icon.png" width="32" height="32" alt="formbricks" title="formbricks" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>formbricks</strong></td>
      <td align="center"><code>4.8.6</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/frappehr/icon.png" width="32" height="32" alt="frappehr" title="frappehr" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>frappehr</strong></td>
      <td align="center"><code>version-15</code></td>
      <td>MariaDB, Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/freescout/icon.png" width="32" height="32" alt="freescout" title="freescout" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>freescout</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/freshrss/icon.png" width="32" height="32" alt="freshrss" title="freshrss" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>freshrss</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/fugu/icon.png" width="32" height="32" alt="fugu" title="fugu" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>fugu</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/funkwhale/icon.png" width="32" height="32" alt="funkwhale" title="funkwhale" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>funkwhale</strong></td>
      <td align="center"><code>1.4</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/garage/icon.png" width="32" height="32" alt="garage" title="garage" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>garage</strong></td>
      <td align="center"><code>v2.3.0</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/ghost/icon.png" width="32" height="32" alt="ghost" title="ghost" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>ghost</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/ghostfolio/icon.png" width="32" height="32" alt="ghostfolio" title="ghostfolio" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>ghostfolio</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://cdn.jsdelivr.net/gh/stackblaze/stack-templates@e1e91781144b4f96bf330019f945a0db1b06534a/services/gitea/icon.png" width="32" height="32" alt="gitea" title="gitea" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>gitea</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/glean/icon.png" width="32" height="32" alt="glean" title="glean" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>glean</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/glpi/icon.png" width="32" height="32" alt="glpi" title="glpi" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>glpi</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/gotify/logo/master/gotify-logo.png" width="32" height="32" alt="gotify" title="gotify" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>gotify</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
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
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/grist/icon.png" width="32" height="32" alt="grist" title="grist" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>grist</strong></td>
      <td align="center"><code>stable</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
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
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/headscale/icon.png" width="32" height="32" alt="headscale" title="headscale" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>headscale</strong></td>
      <td align="center"><code>0.28.0-debug</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/hedgedoc/icon.png" width="32" height="32" alt="hedgedoc" title="hedgedoc" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>hedgedoc</strong></td>
      <td align="center"><code>1.10.8</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/hermes/icon.png" width="32" height="32" alt="hermes" title="hermes" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>hermes</strong></td>
      <td align="center"><code>main</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/hi-events/icon.png" width="32" height="32" alt="hi-events" title="hi-events" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>hi-events</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://github.com/ajnart/homarr/raw/dev/public/imgs/logo/logo-color.svg" width="32" height="32" alt="homarr" title="homarr" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>homarr</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://homebox.software/lilbox.svg" width="32" height="32" alt="homebox" title="homebox" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>homebox</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/gethomepage/homepage/dev/public/homepage.png" width="32" height="32" alt="homepage" title="homepage" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>homepage</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/hop/icon.png" width="32" height="32" alt="hop" title="hop" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>hop</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/hortusfox/icon.png" width="32" height="32" alt="hortusfox" title="hortusfox" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>hortusfox</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/humhub/icon.png" width="32" height="32" alt="humhub" title="humhub" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>humhub</strong></td>
      <td align="center"><code>stable</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/hyperswitch/icon.png" width="32" height="32" alt="hyperswitch" title="hyperswitch" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>hyperswitch</strong></td>
      <td align="center"><code>2026.06.11.0-standalone</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/illa/icon.png" width="32" height="32" alt="illa" title="illa" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>illa</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://cdn.jsdelivr.net/gh/stackblaze/stack-templates@7b68b21d85234eb2a734d361d16b2b939c2cf10b/services/immich/icon.png" width="32" height="32" alt="immich" title="immich" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>immich</strong></td>
      <td align="center"><code>v2</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/infisical/icon.png" width="32" height="32" alt="infisical" title="infisical" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>infisical</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/inventree/icon.png" width="32" height="32" alt="inventree" title="inventree" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>inventree</strong></td>
      <td align="center"><code>stable</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/invoiceninja/icon.png" width="32" height="32" alt="invoiceninja" title="invoiceninja" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>invoiceninja</strong></td>
      <td align="center"><code>5</code></td>
      <td>MariaDB, Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/iomad/icon.png" width="32" height="32" alt="iomad" title="iomad" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>iomad</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/iris/icon.png" width="32" height="32" alt="iris" title="iris" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>iris</strong></td>
      <td align="center"><code>v2.4.20</code></td>
      <td>PostgreSQL (CloudNativePG), RabbitMQ</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/CorentinTh/it-tools/main/public/favicon-32x32.png" width="32" height="32" alt="it-tools" title="it-tools" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>it-tools</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/itop/icon.png" width="32" height="32" alt="itop" title="itop" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>itop</strong></td>
      <td align="center"><code>latest-base</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/jellyfin/icon.png" width="32" height="32" alt="jellyfin" title="jellyfin" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>jellyfin</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/jitsi/icon.png" width="32" height="32" alt="jitsi" title="jitsi" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>jitsi</strong></td>
      <td align="center"><code>stable</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/joomla/icon.png" width="32" height="32" alt="joomla" title="joomla" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>joomla</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/joplin/icon.png" width="32" height="32" alt="joplin" title="joplin" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>joplin</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/13722943?s=200&amp;v=4" width="32" height="32" alt="kanboard" title="kanboard" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>kanboard</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/75163075?s=200&amp;v=4" width="32" height="32" alt="kavita" title="kavita" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>kavita</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/keeweb/icon.png" width="32" height="32" alt="keeweb" title="keeweb" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>keeweb</strong></td>
      <td align="center"><code>1.16.3</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/pentacent/keila/main/.github/assets/logo.svg" width="32" height="32" alt="keila" title="keila" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>keila</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/kener/icon.png" width="32" height="32" alt="kener" title="kener" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>kener</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/keycloak/icon.png" width="32" height="32" alt="keycloak" title="keycloak" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>keycloak</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/kimai/icon.png" width="32" height="32" alt="kimai" title="kimai" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>kimai</strong></td>
      <td align="center"><code>apache</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/kroki/icon.png" width="32" height="32" alt="kroki" title="kroki" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>kroki</strong></td>
      <td align="center"><code>0.31.0</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/lago/icon.png" width="32" height="32" alt="lago" title="lago" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>lago</strong></td>
      <td align="center"><code>v1.48.1</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/langfuse/icon.png" width="32" height="32" alt="langfuse" title="langfuse" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>langfuse</strong></td>
      <td align="center"><code>3</code></td>
      <td>PostgreSQL (CloudNativePG), ClickHouse, Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/languagetool/icon.png" width="32" height="32" alt="languagetool" title="languagetool" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>languagetool</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/leantime/icon.png" width="32" height="32" alt="leantime" title="leantime" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>leantime</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/lemmy/icon.png" width="32" height="32" alt="lemmy" title="lemmy" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>lemmy</strong></td>
      <td align="center"><code>0.19.19</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
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
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/lightdash/icon.png" width="32" height="32" alt="lightdash" title="lightdash" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>lightdash</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), RustFS</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/lightldap/icon.png" width="32" height="32" alt="lightldap" title="lightldap" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>lightldap</strong></td>
      <td align="center"><code>stable</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/limesurvey/icon.png" width="32" height="32" alt="limesurvey" title="limesurvey" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>limesurvey</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/34423368?s=200&amp;v=4" width="32" height="32" alt="linkding" title="linkding" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>linkding</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/linkwarden/icon.png" width="32" height="32" alt="linkwarden" title="linkwarden" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>linkwarden</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/listmonk/icon.png" width="32" height="32" alt="listmonk" title="listmonk" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>listmonk</strong></td>
      <td align="center"><code>v6.1.0</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/litellm/icon.png" width="32" height="32" alt="litellm" title="litellm" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>litellm</strong></td>
      <td align="center"><code>main-latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/localai/icon.png" width="32" height="32" alt="localai" title="localai" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>localai</strong></td>
      <td align="center"><code>latest-cpu</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/logto/icon.png" width="32" height="32" alt="logto" title="logto" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>logto</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/37916028?s=200&amp;v=4" width="32" height="32" alt="lychee" title="lychee" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>lychee</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/magento/icon.png" width="32" height="32" alt="magento" title="magento" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>magento</strong></td>
      <td align="center"><code>php8.3-nginx</code></td>
      <td>MariaDB, OpenSearch</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/mantisbt/icon.png" width="32" height="32" alt="mantisbt" title="mantisbt" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>mantisbt</strong></td>
      <td align="center"><code>2.28.3</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/mastodon/icon.png" width="32" height="32" alt="mastodon" title="mastodon" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>mastodon</strong></td>
      <td align="center"><code>v4.4.18</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/matomo/icon.png" width="32" height="32" alt="matomo" title="matomo" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>matomo</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/mattermost/icon.png" width="32" height="32" alt="mattermost" title="mattermost" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>mattermost</strong></td>
      <td align="center"><code>10.5</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/mautic/icon.png" width="32" height="32" alt="mautic" title="mautic" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>mautic</strong></td>
      <td align="center"><code>5-apache</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/maybe/icon.png" width="32" height="32" alt="maybe" title="maybe" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>maybe</strong></td>
      <td align="center"><code>stable</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/92342333?s=200&amp;v=4" width="32" height="32" alt="mealie" title="mealie" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>mealie</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/mediacms/icon.png" width="32" height="32" alt="mediacms" title="mediacms" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>mediacms</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/memos/icon.png" width="32" height="32" alt="memos" title="memos" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>memos</strong></td>
      <td align="center"><code>stable</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://cdn.jsdelivr.net/gh/stackblaze/stack-templates@f3ef854e5c2c2e94bccc18227bf5c644e6fc2a7e/services/metabase/icon.png" width="32" height="32" alt="metabase" title="metabase" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>metabase</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/metabase-postgres/icon.png" width="32" height="32" alt="metabase-postgres" title="metabase-postgres" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>metabase-postgres</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
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
      <td><img src="https://avatars.githubusercontent.com/u/9411421?s=200&amp;v=4" width="32" height="32" alt="miniflux" title="miniflux" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>miniflux</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/minthcm/icon.png" width="32" height="32" alt="minthcm" title="minthcm" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>minthcm</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/mirotalk-p2p/icon.png" width="32" height="32" alt="mirotalk-p2p" title="mirotalk-p2p" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>mirotalk-p2p</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/misskey/icon.png" width="32" height="32" alt="misskey" title="misskey" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>misskey</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/25832602?s=200&amp;v=4" width="32" height="32" alt="monica" title="monica" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>monica</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/moodle/icon.png" width="32" height="32" alt="moodle" title="moodle" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>moodle</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/45487711?s=200&amp;v=4" width="32" height="32" alt="n8n" title="n8n" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>n8n</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/66823122?s=200&amp;v=4" width="32" height="32" alt="navidrome" title="navidrome" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>navidrome</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/neko-rooms/icon.png" width="32" height="32" alt="neko-rooms" title="neko-rooms" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>neko-rooms</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/netbox/icon.png" width="32" height="32" alt="netbox" title="netbox" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>netbox</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://cdn.jsdelivr.net/gh/stackblaze/stack-templates@6ee4357571945104337fbb75a7852dd0af0b8c4b/services/nextcloud/icon.png" width="32" height="32" alt="nextcloud" title="nextcloud" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>nextcloud</strong></td>
      <td align="center"><code>apache</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/nocobase/icon.png" width="32" height="32" alt="nocobase" title="nocobase" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>nocobase</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://cdn.jsdelivr.net/gh/stackblaze/stack-templates@c44450bb24e2439a4c573aeaf2ee793575f02054/services/nocodb/icon.png" width="32" height="32" alt="nocodb" title="nocodb" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>nocodb</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/nodebb/icon.png" width="32" height="32" alt="nodebb" title="nodebb" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>nodebb</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/nopcommerce/icon.png" width="32" height="32" alt="nopcommerce" title="nopcommerce" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>nopcommerce</strong></td>
      <td align="center"><code>4.90.4</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
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
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/odoo/icon.png" width="32" height="32" alt="odoo" title="odoo" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>odoo</strong></td>
      <td align="center"><code>18.0</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/ollama/icon.png" width="32" height="32" alt="ollama" title="ollama" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>ollama</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/onlyoffice/icon.png" width="32" height="32" alt="onlyoffice" title="onlyoffice" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>onlyoffice</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/onlyoffice/icon.png" width="32" height="32" alt="onlyoffice-docs" title="onlyoffice-docs" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>onlyoffice-docs</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), RabbitMQ, Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://cdn.jsdelivr.net/gh/stackblaze/stack-templates@bddd2bdc0792a05092319696827e99fea190b35d/services/open-webui/icon.png" width="32" height="32" alt="open-webui" title="open-webui" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>open-webui</strong></td>
      <td align="center"><code>main</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/thomiceli/opengist/master/public/opengist.svg" width="32" height="32" alt="opengist" title="opengist" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>opengist</strong></td>
      <td align="center"><code>1</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/openobserve/icon.png" width="32" height="32" alt="openobserve" title="openobserve" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>openobserve</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/openproject/icon.png" width="32" height="32" alt="openproject" title="openproject" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>openproject</strong></td>
      <td align="center"><code>16-slim</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/opnform/icon.png" width="32" height="32" alt="opnform" title="opnform" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>opnform</strong></td>
      <td align="center"><code>1.13.2</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/outline/icon.png" width="32" height="32" alt="outline" title="outline" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>outline</strong></td>
      <td align="center"><code>latest</code></td>
      <td>Valkey, PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/owncast/icon.png" width="32" height="32" alt="owncast" title="owncast" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>owncast</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/owncloud/icon.png" width="32" height="32" alt="owncloud" title="owncloud" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>owncloud</strong></td>
      <td align="center"><code>10.16.3</code></td>
      <td>MariaDB, Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
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
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/papercups/icon.png" width="32" height="32" alt="papercups" title="papercups" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>papercups</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/99562962" width="32" height="32" alt="paperless-ngx-postgresql" title="paperless-ngx-postgresql" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>paperless-ngx-postgresql</strong></td>
      <td align="center"><code>latest</code></td>
      <td>Valkey, PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/papermerge/icon.png" width="32" height="32" alt="papermerge" title="papermerge" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>papermerge</strong></td>
      <td align="center"><code>3.5.3</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/parseable/icon.png" width="32" height="32" alt="parseable" title="parseable" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>parseable</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/4386228?s=200&amp;v=4" width="32" height="32" alt="passbolt" title="passbolt" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>passbolt</strong></td>
      <td align="center"><code>latest-ce</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/passit/icon.png" width="32" height="32" alt="passit" title="passit" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>passit</strong></td>
      <td align="center"><code>stable</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/password-pusher/icon.png" width="32" height="32" alt="password-pusher" title="password-pusher" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>password-pusher</strong></td>
      <td align="center"><code>stable</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/payload/icon.png" width="32" height="32" alt="payload" title="payload" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>payload</strong></td>
      <td align="center"><code>—</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/peertube/icon.png" width="32" height="32" alt="peertube" title="peertube" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>peertube</strong></td>
      <td align="center"><code>production-bullseye</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/penpot/icon.png" width="32" height="32" alt="penpot" title="penpot" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>penpot</strong></td>
      <td align="center"><code>2.16</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/peppermint/icon.png" width="32" height="32" alt="peppermint" title="peppermint" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>peppermint</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/pgadmin/icon.png" width="32" height="32" alt="pgadmin" title="pgadmin" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>pgadmin</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/photon/icon.png" width="32" height="32" alt="photon" title="photon" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>photon</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/photoprism/icon.png" width="32" height="32" alt="photoprism" title="photoprism" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>photoprism</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/75802894?s=200&amp;v=4" width="32" height="32" alt="photoview" title="photoview" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>photoview</strong></td>
      <td align="center"><code>2</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/phpbb/icon.png" width="32" height="32" alt="phpbb" title="phpbb" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>phpbb</strong></td>
      <td align="center"><code>3.3.15</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/picoshare/icon.png" width="32" height="32" alt="picoshare" title="picoshare" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>picoshare</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/9326886" width="32" height="32" alt="piwigo" title="piwigo" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>piwigo</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/pixelfed/icon.png" width="32" height="32" alt="pixelfed" title="pixelfed" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>pixelfed</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB, Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://cdn.jsdelivr.net/gh/stackblaze/stack-templates@4f5f2b23abb891e030a3800ce263a27c1ed93170/services/plane/icon.png" width="32" height="32" alt="plane" title="plane" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>plane</strong></td>
      <td align="center"><code>stable</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey, RustFS, RabbitMQ</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/64215741?s=200&amp;v=4" width="32" height="32" alt="planka" title="planka" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>planka</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://cdn.jsdelivr.net/gh/stackblaze/stack-templates@1b034abb844fe2bb6ce82bbf34bb651285f059a6/services/plausible/icon.png" width="32" height="32" alt="plausible" title="plausible" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>plausible</strong></td>
      <td align="center"><code>v3.0.1</code></td>
      <td>PostgreSQL (CloudNativePG), ClickHouse</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/pleroma/icon.png" width="32" height="32" alt="pleroma" title="pleroma" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>pleroma</strong></td>
      <td align="center"><code>stable</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/pocketbase/icon.png" width="32" height="32" alt="pocketbase" title="pocketbase" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>pocketbase</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/posthog/icon.png" width="32" height="32" alt="posthog" title="posthog" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>posthog</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), ClickHouse, Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/postiz/icon.png" width="32" height="32" alt="postiz" title="postiz" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>postiz</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
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
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/prestashop/icon.png" width="32" height="32" alt="prestashop" title="prestashop" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>prestashop</strong></td>
      <td align="center"><code>8-apache</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/pretix/icon.png" width="32" height="32" alt="pretix" title="pretix" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>pretix</strong></td>
      <td align="center"><code>stable</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/29746989?s=200&amp;v=4" width="32" height="32" alt="psono" title="psono" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>psono</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/pydio/icon.png" width="32" height="32" alt="pydio" title="pydio" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>pydio</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/questdb/icon.png" width="32" height="32" alt="questdb" title="questdb" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>questdb</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/rallly/icon.png" width="32" height="32" alt="rallly" title="rallly" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>rallly</strong></td>
      <td align="center"><code>4</code></td>
      <td>PostgreSQL (CloudNativePG), RustFS</td>
      <td align="center">No</td>
      <td align="center">—</td>
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
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/redash/icon.png" width="32" height="32" alt="redash" title="redash" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>redash</strong></td>
      <td align="center"><code>10.1.0.b50633</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/revolt/icon.png" width="32" height="32" alt="revolt" title="revolt" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>revolt</strong></td>
      <td align="center"><code>v0.13.6</code></td>
      <td>FerretDB, Valkey, RabbitMQ</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/rocketchat/icon.png" width="32" height="32" alt="rocketchat" title="rocketchat" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>rocketchat</strong></td>
      <td align="center"><code>5.4.10</code></td>
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
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/rustdesk/icon.png" width="32" height="32" alt="rustdesk" title="rustdesk" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>rustdesk</strong></td>
      <td align="center"><code>1.1.15</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/rustfs/icon.png" width="32" height="32" alt="rustfs" title="rustfs" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>rustfs</strong></td>
      <td align="center"><code>latest</code></td>
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
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/saleor/icon.png" width="32" height="32" alt="saleor" title="saleor" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>saleor</strong></td>
      <td align="center"><code>3.20</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/saltcorn/icon.png" width="32" height="32" alt="saltcorn" title="saltcorn" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>saltcorn</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/seafile/icon.png" width="32" height="32" alt="seafile" title="seafile" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>seafile</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/searxng/icon.png" width="32" height="32" alt="searxng" title="searxng" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>searxng</strong></td>
      <td align="center"><code>latest</code></td>
      <td>Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/seaweedfs/icon.png" width="32" height="32" alt="seaweedfs" title="seaweedfs" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>seaweedfs</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
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
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/serpbear/icon.png" width="32" height="32" alt="serpbear" title="serpbear" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>serpbear</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/sharkey/icon.png" width="32" height="32" alt="sharkey" title="sharkey" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>sharkey</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/go-shiori/shiori/master/internal/view/assets/res/apple-touch-icon-152x152.png" width="32" height="32" alt="shiori" title="shiori" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>shiori</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/shlink/icon.png" width="32" height="32" alt="shlink" title="shlink" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>shlink</strong></td>
      <td align="center"><code>stable</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/shopware/icon.png" width="32" height="32" alt="shopware" title="shopware" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>shopware</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB, Valkey</td>
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
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/snipe-it/icon.png" width="32" height="32" alt="snipe-it" title="snipe-it" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>snipe-it</strong></td>
      <td align="center"><code>v8.6.2</code></td>
      <td>MariaDB, Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://cdn.jsdelivr.net/gh/walkxcode/dashboard-icons/png/vscode.png" width="32" height="32" alt="stackblaze-workspace" title="stackblaze-workspace" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>stackblaze-workspace</strong></td>
      <td align="center"><code>—</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/stalwart-mail/icon.png" width="32" height="32" alt="stalwart-mail" title="stalwart-mail" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>stalwart-mail</strong></td>
      <td align="center"><code>v0.16</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/stirling-pdf/icon.png" width="32" height="32" alt="sterlingpdf" title="sterlingpdf" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>sterlingpdf</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://cdn.jsdelivr.net/gh/stackblaze/stack-templates@0522dea0f303d9707196108356d351e1ebde3b59/services/stirling-pdf/icon.png" width="32" height="32" alt="stirling-pdf" title="stirling-pdf" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>stirling-pdf</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/strapi/icon.png" width="32" height="32" alt="strapi" title="strapi" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>strapi</strong></td>
      <td align="center"><code>5.30.2</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/suitecrm/icon.png" width="32" height="32" alt="suitecrm" title="suitecrm" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>suitecrm</strong></td>
      <td align="center"><code>8</code></td>
      <td>MariaDB, Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/superset/icon.png" width="32" height="32" alt="superset" title="superset" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>superset</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/syncthing/icon.png" width="32" height="32" alt="syncthing" title="syncthing" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>syncthing</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/taiga/icon.png" width="32" height="32" alt="taiga" title="taiga" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>taiga</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), RabbitMQ</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/tandoor/icon.svg" width="32" height="32" alt="tandoor" title="tandoor" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>tandoor</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
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
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/teable/icon.png" width="32" height="32" alt="teable" title="teable" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>teable</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/temporal/icon.png" width="32" height="32" alt="temporal" title="temporal" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>temporal</strong></td>
      <td align="center"><code>1.29</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/38871878" width="32" height="32" alt="textbee" title="textbee" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>textbee</strong></td>
      <td align="center"><code>latest</code></td>
      <td>Document DB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/timescaledb/icon.png" width="32" height="32" alt="timescaledb" title="timescaledb" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>timescaledb</strong></td>
      <td align="center"><code>latest-pg16</code></td>
      <td>—</td>
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
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/tolgee/icon.png" width="32" height="32" alt="tolgee" title="tolgee" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>tolgee</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/totaljs-flow/icon.png" width="32" height="32" alt="totaljs-flow" title="totaljs-flow" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>totaljs-flow</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/tracardi/icon.png" width="32" height="32" alt="tracardi" title="tracardi" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>tracardi</strong></td>
      <td align="center"><code>1.1.6</code></td>
      <td>MariaDB, Valkey, OpenSearch</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/traduora/icon.png" width="32" height="32" alt="traduora" title="traduora" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>traduora</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/traggo/icon.png" width="32" height="32" alt="traggo" title="traggo" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>traggo</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/trilium/icon.png" width="32" height="32" alt="trilium" title="trilium" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>trilium</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/trudesk/icon.png" width="32" height="32" alt="trudesk" title="trudesk" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>trudesk</strong></td>
      <td align="center"><code>1</code></td>
      <td>Document DB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://cdn.jsdelivr.net/gh/stackblaze/stack-templates@54dbcb3cf1eb0643ab8ec7b9297ceabcd652f694/services/twenty/icon.png" width="32" height="32" alt="twenty" title="twenty" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>twenty</strong></td>
      <td align="center"><code>v2.16.1</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://docs.2fauth.app/static/2fauth_dark.png" width="32" height="32" alt="twofauth" title="twofauth" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>twofauth</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://cdn.jsdelivr.net/gh/stackblaze/stack-templates@45afbcf915e2937f16515a4a5b41352ac48cf714/services/typebot/icon.png" width="32" height="32" alt="typebot" title="typebot" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>typebot</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/umami/icon.png" width="32" height="32" alt="umami" title="umami" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>umami</strong></td>
      <td align="center"><code>postgresql-latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/unibee/icon.png" width="32" height="32" alt="unibee" title="unibee" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>unibee</strong></td>
      <td align="center"><code>v1.9.0</code></td>
      <td>MariaDB, Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/23053233?s=200&amp;v=4" width="32" height="32" alt="unleash" title="unleash" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>unleash</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/unomi/icon.png" width="32" height="32" alt="unomi" title="unomi" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>unomi</strong></td>
      <td align="center"><code>3.0.0</code></td>
      <td>Elasticsearch</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://cdn.jsdelivr.net/gh/stackblaze/stack-templates@3664d86/services/uptime-kuma/icon.png" width="32" height="32" alt="uptime-kuma" title="uptime-kuma" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>uptime-kuma</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/uvdesk/icon.png" width="32" height="32" alt="uvdesk" title="uvdesk" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>uvdesk</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/vaultwarden/icon.png" width="32" height="32" alt="vaultwarden" title="vaultwarden" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>vaultwarden</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/verdaccio/icon.png" width="32" height="32" alt="verdaccio" title="verdaccio" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>verdaccio</strong></td>
      <td align="center"><code>latest</code></td>
      <td>—</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/vikunja/icon.png" width="32" height="32" alt="vikunja" title="vikunja" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>vikunja</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/wagtail/icon.png" width="32" height="32" alt="wagtail" title="wagtail" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>wagtail</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/4573139?s=200&amp;v=4" width="32" height="32" alt="wallabag" title="wallabag" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>wallabag</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/wekan/icon.png" width="32" height="32" alt="wekan" title="wekan" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>wekan</strong></td>
      <td align="center"><code>v8.74</code></td>
      <td>Document DB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/wger/icon.png" width="32" height="32" alt="wger" title="wger" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>wger</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
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
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/wikijs/icon.png" width="32" height="32" alt="wikijs" title="wikijs" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>wikijs</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/woocommerce/icon.png" width="32" height="32" alt="woocommerce" title="woocommerce" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>woocommerce</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/wordpress/icon.png" width="32" height="32" alt="wordpress" title="wordpress" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>wordpress</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/wordpress-multisite/icon.png" width="32" height="32" alt="wordpress-multisite" title="wordpress-multisite" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>wordpress-multisite</strong></td>
      <td align="center"><code>latest</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/xwiki/icon.png" width="32" height="32" alt="xwiki" title="xwiki" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>xwiki</strong></td>
      <td align="center"><code>stable-postgres-tomcat</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/yopass/icon.png" width="32" height="32" alt="yopass" title="yopass" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>yopass</strong></td>
      <td align="center"><code>latest</code></td>
      <td>Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/yourls/icon.png" width="32" height="32" alt="yourls" title="yourls" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>yourls</strong></td>
      <td align="center"><code>1.10-apache</code></td>
      <td>MariaDB</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/zammad/icon.png" width="32" height="32" alt="zammad" title="zammad" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>zammad</strong></td>
      <td align="center"><code>stable</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://avatars.githubusercontent.com/u/1396645" width="32" height="32" alt="zipline" title="zipline" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>zipline</strong></td>
      <td align="center"><code>latest</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/zitadel/icon.png" width="32" height="32" alt="zitadel" title="zitadel" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>zitadel</strong></td>
      <td align="center"><code>stable</code></td>
      <td>PostgreSQL (CloudNativePG)</td>
      <td align="center">No</td>
      <td align="center">—</td>
    </tr>
    <tr>
      <td><img src="https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/zulip/icon.png" width="32" height="32" alt="zulip" title="zulip" style="vertical-align:middle;border-radius:4px;" /></td>
      <td><strong>zulip</strong></td>
      <td align="center"><code>11.6-0</code></td>
      <td>PostgreSQL (CloudNativePG), Valkey, RabbitMQ, Memcached</td>
      <td align="center">No</td>
      <td align="center">—</td>
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

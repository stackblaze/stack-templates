# stack-templates

Kubero template catalog for the **stackblaze fork** of Kubero. Public so any
running Kubero in the stackblaze SaaS can fetch from `raw.githubusercontent.com`
anonymously.

Forked from upstream `kubero-dev/templates` + `kubero-dev/kubero/services/` and
consolidated into a single repo so the catalog has zero runtime dependency on
`kubero-dev/*`.

## Layout

- **`index.json`** — main catalog (171 services). Each entry's `template`
  field points at `services/<name>/app.yaml` in this repo.
- **`index-frameworks.json`** — frameworks catalog (2 entries).
- **`services/<name>/app.yaml`** — the per-template body kubero pulls when
  the user clicks Install. Each entry typically also has `service.yaml` and
  a `logo.svg`.

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

## Editing template bodies

To replace cluster-specific defaults (e.g. swap a hard-coded
`storageClassName: standard` for the cluster's default), edit the
relevant `services/<name>/app.yaml` directly. No build step; the next
template install picks it up on the next fetch.

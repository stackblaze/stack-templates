#!/usr/bin/env python3
"""Emit the gen-templates workflow JS with the 138-app list embedded."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
arr = (HERE / "_apps.jsarr.txt").read_text(encoding="utf-8")

JS = r'''export const meta = {
  name: 'generate-stack-templates',
  description: 'Research and spec 138 missing Kubero app templates (writes JSON specs to scripts/_specs)',
  phases: [{ title: 'Research', detail: 'one agent per app -> writes a services spec JSON' }],
}

const SPEC_DIR = 'C:/Users/dean/Documents/stackblaze/stack-templates/scripts/_specs'

const APPS = [
__APPS__
]

const ACK = {
  type: 'object',
  additionalProperties: false,
  properties: {
    slug: { type: 'string' },
    status: { type: 'string', enum: ['ok', 'failed'] },
    image: { type: 'string', description: 'repository:tag actually chosen' },
    addons: { type: 'array', items: { type: 'string' } },
    containerPort: { type: 'string' },
    note: { type: 'string', description: 'short note: companions documented, uncertainty, or failure reason' },
  },
  required: ['slug', 'status'],
}

function promptFor(app) {
  const complexNote = app.complex
    ? 'NOTE: This app is a MULTI-CONTAINER stack. Produce a template for the PRIMARY web/server image ONLY, wire the operator add-ons it needs, and clearly describe the companion services (worker, scheduler, proxy, frontend, ML, federation queue, etc.) in the installation note with their image names. Do NOT try to put multiple images in one template.'
    : 'This app should map to a single primary image plus operator add-ons.'
  return [
'You are producing ONE Kubero app template spec for the self-hosted application below, following this repo established convention EXACTLY.',
'',
'APP: ' + app.title,
'SLUG: ' + app.slug,
complexNote,
'',
'== WHAT TO DO ==',
'1. Identify the canonical, actively-maintained Docker image for self-hosting this app. Prefer the OFFICIAL image on Docker Hub or ghcr.io. Pick a stable tag (a pinned major like "10-apache" or a maintained channel like "latest"/"stable"/"release"). Avoid bleeding-edge or arch-specific tags.',
'2. Determine the HTTP container port the app listens on (as a STRING).',
'3. Decide which operator ADD-ONS it needs. Choose ONLY from: postgres, mariadb, valkey, documentdb, clickhouse, rabbitmq, memcached. Prefer postgres when the app supports both postgres and mysql. If the app stores everything in SQLite/files, use NO add-on and a persistent volume instead. Do not invent other datastores; if it truly needs e.g. Elasticsearch or S3, note that in the installation field and omit it from addons.',
'4. Set environment variables the app needs to boot and connect to its add-ons, using the EXACT in-cluster hostnames below.',
'5. Add extraVolumes for any path holding user data, uploads, or config (size 1Gi-5Gi). Stateless apps get an empty array.',
'6. Rely on your own knowledge first. Do AT MOST 2 web lookups, and only to confirm the image repo/tag or a critical env var name. Be efficient.',
'',
'== ADD-ON ENDPOINTS (use these literal hostnames; <name> = the slug "' + app.slug + '") ==',
'- postgres : host <name>-postgresql-rw  port 5432 ; URI postgresql://<user>:<pass>@<name>-postgresql-rw:5432/<db>',
'- mariadb  : host <name>-mysql          port 3306',
'- valkey   : host rfr-<name>-valkey-readwrite port 6379 (NO password) ; URI redis://rfr-<name>-valkey-readwrite:6379',
'- documentdb: host documentdb-service-<name>-documentdb port 10260 (TLS+SCRAM, user mongoadmin) ; URI mongodb://<user>:<pass>@documentdb-service-<name>-documentdb:10260/?directConnection=true&authMechanism=SCRAM-SHA-256&tls=true&tlsAllowInvalidCertificates=true&replicaSet=rs0',
'- clickhouse: host clickhouse-<name>-clickhouse port 8123 (user admin)',
'- rabbitmq : host <name>-rabbitmq',
'- memcached: <name>-memcached:11211',
'',
'== CONVENTIONS ==',
'- Default db name / user / password = the slug (e.g. "' + app.slug + '"). These are template defaults meant to be rotated; that is fine.',
'- For secret keys that MUST be random, use an obvious placeholder VALUE like "replace-with-openssl-rand-hex-32" (or -base64-32) and mention rotation in installation.',
'- When the app needs to know its own public URL, use the literal token {{KUBERO_APP_URL}} (full https URL) or {{KUBERO_APP_HOST}} (host only) as the env value.',
'- containerPort is a STRING. Every env value is a STRING.',
'- Keep the add-on "name" equal to the slug. The hostnames in your env vars MUST match that name.',
'',
'== ADD-ON OBJECT SHAPE ==',
'  postgres/mariadb : {"type":"postgres","name":"' + app.slug + '","db":"...","user":"...","password":"..."}',
'  valkey           : {"type":"valkey","name":"' + app.slug + '"}',
'  documentdb       : {"type":"documentdb","name":"' + app.slug + '","user":"mongoadmin","password":"' + app.slug + '"}',
'  clickhouse       : {"type":"clickhouse","name":"' + app.slug + '","password":"' + app.slug + '"}',
'  rabbitmq         : {"type":"rabbitmq","name":"' + app.slug + '","user":"' + app.slug + '","password":"' + app.slug + '"}',
'  memcached        : {"type":"memcached","name":"' + app.slug + '"}',
'',
'== OUTPUT (REQUIRED) ==',
'Write a UTF-8 JSON file to EXACTLY this path using the Write tool:',
'  ' + SPEC_DIR + '/' + app.slug + '.json',
'The JSON MUST have this shape (strings unless noted):',
'{',
'  "slug": "' + app.slug + '",',
'  "title": "' + app.title + '",',
'  "description": "one concise sentence, under 160 chars",',
'  "source": "https://github.com/ORG/REPO",',
'  "website": "https://...",',
'  "icon": "https://avatars.githubusercontent.com/u/NNN?s=200&v=4 (prefer the project org GitHub avatar)",',
'  "categories": ["pick 2-3 from: work, utilities, productivity, collaboration, development, communication, security, cms, documentation, data, social, media, e-commerce, helpdesk, automation, storage, monitoring, crm, erp, identity, ai, finance"],',
'  "installation": "setup notes: what to rotate, companion services to deploy, first-run steps",',
'  "screenshots": ["https://... (0-2 urls, [] if none known)"],',
'  "links": ["https://docs... (0-2 urls)"],',
'  "license": "e.g. MIT License / GNU Affero General Public License v3.0 / Other",',
'  "spdx_id": "e.g. MIT / AGPL-3.0 / NOASSERTION",',
'  "stars": 1234,',
'  "language": "primary language e.g. PHP",',
'  "image": {"repository": "org/image", "tag": "stable", "containerPort": "8080", "command": []},',
'  "envVars": [{"name": "KEY", "value": "VALUE"}],',
'  "addons": [ add-on objects per the shapes above, or [] ],',
'  "extraVolumes": [{"mountPath": "/data", "name": "' + app.slug + '-data", "size": "2Gi"}]',
'}',
'Include "command" only if the image needs a custom entrypoint (else use []).',
'After writing the file, return the ack object. Set status "ok" if you wrote a complete, deployable spec; "failed" (with reason in note) if you could not find a usable self-host image.',
  ].join('\n')
}

phase('Research')
log('Researching ' + APPS.length + ' app templates...')

const results = await parallel(
  APPS.map((app) => () =>
    agent(promptFor(app), {
      label: app.slug,
      phase: 'Research',
      schema: ACK,
      agentType: 'general-purpose',
    })
  )
)

const acks = results.filter(Boolean)
const ok = acks.filter((r) => r.status === 'ok')
const failed = acks.filter((r) => r.status !== 'ok')
log('Specs OK: ' + ok.length + '/' + APPS.length + ' ; failed: ' + failed.length)

return {
  total: APPS.length,
  ok: ok.length,
  failed: failed.map((f) => ({ slug: f.slug, note: f.note })),
  nullReturns: APPS.length - acks.length,
}
'''

JS = JS.replace("__APPS__", arr)
out = HERE / "gen-templates.workflow.js"
out.write_text(JS, encoding="utf-8")
print(f"wrote {out} ({len(JS)} bytes)")

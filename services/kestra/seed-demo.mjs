#!/usr/bin/env node
/**
 * Kestra demo data: an AI triage flow that calls a model hosted on Stackblaze.
 *
 * Loads the flow `stackblaze.demo / triage-ticket` into a running Kestra (from
 * the catalog template) through Kestra's API, and stores the model's
 * OpenAI-compatible base URL, key and name in that namespace's KV store, where
 * the flow reads them with kv(). Safe to run again: the KV values and the flow
 * are replaced.
 *
 *   node services/kestra/seed-demo.mjs \
 *     --url https://kestra-xxxx.stackblaze.app \
 *     --email admin@stackblaze.app --password "$ADMIN_PASSWORD" \
 *     --ai-url https://api.stackblaze.cloud/api/inference/<id>/v1 \
 *     --ai-key "$AI_MODEL_KEY" --ai-model qwen3-14b
 *
 * --password and --ai-key may also come from KESTRA_PASSWORD / AI_MODEL_KEY.
 * Node 18+ (global fetch); no dependencies.
 */

const NAMESPACE = 'stackblaze.demo';
const FLOW_ID = 'triage-ticket';

const FLOW = `id: ${FLOW_ID}
namespace: ${NAMESPACE}
description: >-
  Sends a support ticket to an AI model hosted on Stackblaze (an
  OpenAI-compatible endpoint) and returns a JSON triage decision. The model's
  URL, key and name are in this namespace's KV store (AI_URL, AI_KEY, AI_MODEL).

inputs:
  - id: ticket
    type: STRING
    defaults: Patient reports chest pain on exertion, relieved by rest, 58 years old.

tasks:
  - id: triage
    type: io.kestra.plugin.core.http.Request
    uri: "{{ kv('AI_URL') }}/chat/completions"
    method: POST
    contentType: application/json
    headers:
      Authorization: "Bearer {{ kv('AI_KEY') }}"
    options:
      timeout:
        # A sleeping model wakes on the first request (about a minute).
        readIdleTimeout: PT5M
    body: |
      {
        "model": "{{ kv('AI_MODEL') }}",
        "response_format": { "type": "json_object" },
        "messages": [
          { "role": "system", "content": "You triage support tickets. Reply with JSON only: {\\"priority\\": \\"low|medium|high\\", \\"team\\": string, \\"reason\\": string}." },
          { "role": "user", "content": {{ inputs.ticket | toJson }} }
        ]
      }

  - id: result
    type: io.kestra.plugin.core.output.OutputValues
    values:
      decision: "{{ outputs.triage.body | jq('.choices[0].message.content') | first }}"
      reasoning: "{{ outputs.triage.body | jq('.choices[0].message.reasoning_content // \\"\\"') | first }}"
      tokens: "{{ outputs.triage.body | jq('.usage.total_tokens') | first }}"
`;

function args() {
  const out = {};
  const a = process.argv.slice(2);
  for (let i = 0; i < a.length; i++) {
    if (!a[i].startsWith('--')) continue;
    out[a[i].slice(2)] = a[i + 1];
    i++;
  }
  return out;
}

const opt = args();
const base = String(opt.url || '').replace(/\/+$/, '');
const email = opt.email || 'admin@stackblaze.app';
const password = opt.password || process.env.KESTRA_PASSWORD;
const aiUrl = String(opt['ai-url'] || '').replace(/\/+$/, '');
const aiKey = opt['ai-key'] || process.env.AI_MODEL_KEY;
const aiModel = opt['ai-model'];

for (const [name, v] of Object.entries({ '--url': base, '--password': password, '--ai-url': aiUrl, '--ai-key': aiKey, '--ai-model': aiModel })) {
  if (!v) {
    console.error(`[kestra-seed] missing ${name}`);
    process.exit(2);
  }
}

const auth = 'Basic ' + Buffer.from(`${email}:${password}`).toString('base64');
const api = `${base}/api/v1/main`;

async function call(method, path, body, type = 'application/json') {
  const res = await fetch(path.startsWith('http') ? path : `${api}${path}`, {
    method,
    headers: { Authorization: auth, ...(body !== undefined ? { 'Content-Type': type } : {}) },
    body,
  });
  const text = await res.text();
  return { status: res.status, ok: res.ok, text };
}

async function waitForKestra() {
  for (let i = 0; i < 90; i++) {
    try {
      const r = await fetch(`${base}/ping`);
      if (r.ok) return;
    } catch {
      /* not up yet */
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
  throw new Error(`Kestra did not answer ${base}/ping`);
}

async function main() {
  await waitForKestra();
  const who = await call('GET', '/flows/search?size=1');
  if (who.status === 401) throw new Error('sign-in refused: check --email / --password');

  for (const [key, value] of [['AI_URL', aiUrl], ['AI_KEY', aiKey], ['AI_MODEL', aiModel]]) {
    const r = await call('PUT', `/namespaces/${NAMESPACE}/kv/${key}`, JSON.stringify(value));
    if (!r.ok) throw new Error(`KV ${key}: HTTP ${r.status} ${r.text.slice(0, 200)}`);
  }
  console.log(`[kestra-seed] KV AI_URL, AI_KEY, AI_MODEL set in ${NAMESPACE}`);

  let r = await call('PUT', `/flows/${NAMESPACE}/${FLOW_ID}`, FLOW, 'application/x-yaml');
  if (r.status === 404) r = await call('POST', '/flows', FLOW, 'application/x-yaml');
  if (!r.ok) throw new Error(`flow: HTTP ${r.status} ${r.text.slice(0, 300)}`);
  console.log(`[kestra-seed] flow ${NAMESPACE} / ${FLOW_ID} loaded`);
  console.log(`[kestra-seed] open ${base}/ui/main/flows/edit/${NAMESPACE}/${FLOW_ID} and click Execute`);
}

main().catch((e) => {
  console.error(`[kestra-seed] ${e.message}`);
  process.exit(1);
});

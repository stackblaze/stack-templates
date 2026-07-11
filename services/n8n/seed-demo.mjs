#!/usr/bin/env node
/**
 * Seed Stackblaze demo workflows on first boot (no sticky notes).
 * Invoked by kubero-entrypoint.sh when STACKBLAZE_LOAD_DEMO_DATA=true.
 *
 * Env:
 *   STACKBLAZE_APP_URL          (default http://127.0.0.1:5678)
 *   STACKBLAZE_DEMO_EMAIL       (default demo@stackblaze.local)
 *   STACKBLAZE_DEMO_PASSWORD    (default changeme)
 *   STACKBLAZE_DEMO_FIRST_NAME  (default Demo)
 *   STACKBLAZE_DEMO_LAST_NAME   (default User)
 *
 * One-off QA:
 *   node seed-demo.mjs --url https://your-n8n.stackblaze.app --force
 */

import { randomUUID } from 'node:crypto';

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--url') args.url = argv[++i];
    else if (a === '--email') args.email = argv[++i];
    else if (a === '--password') args.password = argv[++i];
    else if (a === '--force') args.force = true;
  }
  return args;
}

function leadCapture() {
  const webhookId = randomUUID();
  const nodes = [
    {
      id: randomUUID(),
      name: 'Website signup',
      type: 'n8n-nodes-base.webhook',
      typeVersion: 2,
      position: [240, 180],
      webhookId,
      parameters: {
        httpMethod: 'POST',
        path: 'lead-signup',
        responseMode: 'responseNode',
        options: {},
      },
    },
    {
      id: randomUUID(),
      name: 'Normalize payload',
      type: 'n8n-nodes-base.set',
      typeVersion: 3.4,
      position: [460, 180],
      parameters: {
        mode: 'manual',
        duplicateItem: false,
        assignments: {
          assignments: [
            { id: '1', name: 'email', value: '={{ $json.body.email }}', type: 'string' },
            { id: '2', name: 'name', value: '={{ $json.body.name }}', type: 'string' },
            { id: '3', name: 'source', value: 'website', type: 'string' },
          ],
        },
        options: {},
      },
    },
    {
      id: randomUUID(),
      name: 'Send to CRM',
      type: 'n8n-nodes-base.httpRequest',
      typeVersion: 4.2,
      position: [680, 180],
      parameters: {
        method: 'POST',
        url: 'https://httpbin.org/post',
        sendBody: true,
        specifyBody: 'json',
        jsonBody: '={{ JSON.stringify($json) }}',
        options: {},
      },
    },
    {
      id: randomUUID(),
      name: 'CRM accepted?',
      type: 'n8n-nodes-base.if',
      typeVersion: 2.2,
      position: [900, 180],
      parameters: {
        conditions: {
          options: { caseSensitive: true, leftValue: '', typeValidation: 'strict' },
          conditions: [
            {
              id: '1',
              leftValue: '={{ $json.statusCode || 200 }}',
              rightValue: 200,
              operator: { type: 'number', operation: 'equals' },
            },
          ],
          combinator: 'and',
        },
        options: {},
      },
    },
    {
      id: randomUUID(),
      name: 'Mark as qualified',
      type: 'n8n-nodes-base.set',
      typeVersion: 3.4,
      position: [1120, 80],
      parameters: {
        mode: 'manual',
        assignments: {
          assignments: [{ id: '1', name: 'status', value: 'qualified', type: 'string' }],
        },
        options: {},
      },
    },
    {
      id: randomUUID(),
      name: 'Queue retry',
      type: 'n8n-nodes-base.set',
      typeVersion: 3.4,
      position: [1120, 280],
      parameters: {
        mode: 'manual',
        assignments: {
          assignments: [{ id: '1', name: 'status', value: 'retry', type: 'string' }],
        },
        options: {},
      },
    },
    {
      id: randomUUID(),
      name: 'Respond to site',
      type: 'n8n-nodes-base.respondToWebhook',
      typeVersion: 1.1,
      position: [1340, 180],
      parameters: {
        respondWith: 'json',
        responseBody: '={{ { ok: true, status: $json.status } }}',
        options: {},
      },
    },
  ];
  const connections = {
    'Website signup': { main: [[{ node: 'Normalize payload', type: 'main', index: 0 }]] },
    'Normalize payload': { main: [[{ node: 'Send to CRM', type: 'main', index: 0 }]] },
    'Send to CRM': { main: [[{ node: 'CRM accepted?', type: 'main', index: 0 }]] },
    'CRM accepted?': {
      main: [
        [{ node: 'Mark as qualified', type: 'main', index: 0 }],
        [{ node: 'Queue retry', type: 'main', index: 0 }],
      ],
    },
    'Mark as qualified': { main: [[{ node: 'Respond to site', type: 'main', index: 0 }]] },
    'Queue retry': { main: [[{ node: 'Respond to site', type: 'main', index: 0 }]] },
  };
  return {
    name: 'Stackblaze demo — Lead capture',
    nodes,
    connections,
    settings: { executionOrder: 'v1' },
  };
}

function dailyDigest() {
  const nodes = [
    {
      id: randomUUID(),
      name: 'Every morning',
      type: 'n8n-nodes-base.scheduleTrigger',
      typeVersion: 1.2,
      position: [240, 180],
      parameters: {
        rule: { interval: [{ field: 'cronExpression', expression: '0 8 * * *' }] },
      },
    },
    {
      id: randomUUID(),
      name: 'Fetch repo stats',
      type: 'n8n-nodes-base.httpRequest',
      typeVersion: 4.2,
      position: [460, 180],
      parameters: {
        method: 'GET',
        url: 'https://api.github.com/repos/n8n-io/n8n',
        options: {},
      },
    },
    {
      id: randomUUID(),
      name: 'Build summary',
      type: 'n8n-nodes-base.set',
      typeVersion: 3.4,
      position: [680, 180],
      parameters: {
        mode: 'manual',
        assignments: {
          assignments: [
            { id: '1', name: 'stars', value: '={{ $json.stargazers_count }}', type: 'number' },
            { id: '2', name: 'forks', value: '={{ $json.forks_count }}', type: 'number' },
            { id: '3', name: 'open_issues', value: '={{ $json.open_issues_count }}', type: 'number' },
          ],
        },
        options: {},
      },
    },
    {
      id: randomUUID(),
      name: 'Format digest',
      type: 'n8n-nodes-base.code',
      typeVersion: 2,
      position: [900, 180],
      parameters: {
        jsCode:
          "const d = $input.first().json;\nreturn [{ json: { message: `Daily digest: ${d.stars} stars · ${d.forks} forks · ${d.open_issues} open issues` } }];",
      },
    },
  ];
  const connections = {
    'Every morning': { main: [[{ node: 'Fetch repo stats', type: 'main', index: 0 }]] },
    'Fetch repo stats': { main: [[{ node: 'Build summary', type: 'main', index: 0 }]] },
    'Build summary': { main: [[{ node: 'Format digest', type: 'main', index: 0 }]] },
  };
  return {
    name: 'Stackblaze demo — Daily digest',
    nodes,
    connections,
    settings: { executionOrder: 'v1' },
  };
}

function aiSummarize() {
  const nodes = [
    {
      id: randomUUID(),
      name: 'On new email',
      type: 'n8n-nodes-base.manualTrigger',
      typeVersion: 1,
      position: [240, 180],
      parameters: {},
    },
    {
      id: randomUUID(),
      name: 'Extract fields',
      type: 'n8n-nodes-base.set',
      typeVersion: 3.4,
      position: [460, 180],
      parameters: {
        mode: 'manual',
        assignments: {
          assignments: [
            { id: '1', name: 'subject', value: 'Q3 pipeline update', type: 'string' },
            {
              id: '2',
              name: 'body',
              value: 'Closed 3 deals this week. Next focus: enterprise renewals.',
              type: 'string',
            },
          ],
        },
        options: {},
      },
    },
    {
      id: randomUUID(),
      name: 'Summarize with AI',
      type: 'n8n-nodes-base.code',
      typeVersion: 2,
      position: [680, 180],
      parameters: {
        jsCode:
          "const j = $input.first().json;\nreturn [{ json: { summary: `TL;DR: ${j.subject} — ${j.body}` } }];",
      },
    },
    {
      id: randomUUID(),
      name: 'Save note',
      type: 'n8n-nodes-base.set',
      typeVersion: 3.4,
      position: [900, 180],
      parameters: {
        mode: 'manual',
        assignments: {
          assignments: [
            { id: '1', name: 'note', value: '={{ $json.summary }}', type: 'string' },
            { id: '2', name: 'saved', value: true, type: 'boolean' },
          ],
        },
        options: {},
      },
    },
  ];
  const connections = {
    'On new email': { main: [[{ node: 'Extract fields', type: 'main', index: 0 }]] },
    'Extract fields': { main: [[{ node: 'Summarize with AI', type: 'main', index: 0 }]] },
    'Summarize with AI': { main: [[{ node: 'Save note', type: 'main', index: 0 }]] },
  };
  return {
    name: 'Stackblaze demo — AI email summary',
    nodes,
    connections,
    settings: { executionOrder: 'v1' },
  };
}

async function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function waitForSettings(base) {
  for (let i = 0; i < 90; i++) {
    try {
      const r = await fetch(`${base}/rest/settings`);
      if (r.ok) return r.json();
    } catch {
      /* retry */
    }
    await sleep(2000);
  }
  throw new Error('n8n /rest/settings not ready');
}

function cookieFrom(res) {
  const raw = res.headers.getSetCookie?.() || [];
  if (raw.length) {
    const match = raw.join(';').match(/n8n-auth=[^;]+/);
    if (match) return match[0];
  }
  const single = res.headers.get('set-cookie');
  return single?.match(/n8n-auth=[^;]+/)?.[0] || null;
}

async function ensureOwner(base, email, password, firstName, lastName) {
  const settings = await waitForSettings(base);
  const showSetup = settings?.data?.userManagement?.showSetupOnFirstLoad;
  if (showSetup) {
    const setup = await fetch(`${base}/rest/owner/setup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, firstName, lastName, password }),
    });
    const body = await setup.text();
    if (!setup.ok && !/already/i.test(body)) {
      throw new Error(`owner setup failed: ${setup.status} ${body.slice(0, 200)}`);
    }
    console.log('[n8n-seed] owner created', email);
  } else {
    console.log('[n8n-seed] owner already configured');
  }
}

async function login(base, email, password) {
  const res = await fetch(`${base}/rest/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ emailOrLdapLoginId: email, password }),
  });
  if (!res.ok) {
    throw new Error(`login failed: ${res.status} ${(await res.text()).slice(0, 200)}`);
  }
  const cookie = cookieFrom(res);
  if (!cookie) throw new Error('login succeeded but no n8n-auth cookie');
  return cookie;
}

async function main() {
  const args = parseArgs(process.argv);
  const base = (args.url || process.env.STACKBLAZE_APP_URL || 'http://127.0.0.1:5678').replace(
    /\/$/,
    '',
  );
  const email = args.email || process.env.STACKBLAZE_DEMO_EMAIL || 'demo@stackblaze.local';
  const password = args.password || process.env.STACKBLAZE_DEMO_PASSWORD || 'changeme';
  const firstName = process.env.STACKBLAZE_DEMO_FIRST_NAME || 'Demo';
  const lastName = process.env.STACKBLAZE_DEMO_LAST_NAME || 'User';

  await ensureOwner(base, email, password, firstName, lastName);
  const cookie = await login(base, email, password);
  const headers = { cookie, 'Content-Type': 'application/json' };

  const list = await fetch(`${base}/rest/workflows?limit=50`, { headers });
  const listed = await list.json();
  const existing = (listed.data || []).filter((w) => w.name?.startsWith('Stackblaze demo'));
  if (existing.length >= 3 && !args.force) {
    console.log('[n8n-seed] demo workflows already present — skipping create');
    console.log(existing.map((w) => ({ id: w.id, name: w.name })));
    return;
  }

  for (const wf of [leadCapture(), dailyDigest(), aiSummarize()]) {
    if (!args.force && existing.some((e) => e.name === wf.name)) {
      console.log('[n8n-seed] skip existing', wf.name);
      continue;
    }
    const r = await fetch(`${base}/rest/workflows`, {
      method: 'POST',
      headers,
      body: JSON.stringify(wf),
    });
    const body = await r.json();
    console.log('[n8n-seed] create', r.status, body.data?.id, body.data?.name || body.message);
  }
}

main().catch((err) => {
  console.error('[n8n-seed]', err);
  process.exit(1);
});

#!/usr/bin/env python3
"""seed.py <vars.json> <url>: demo flows for screenshots/recording (idempotent by display name).
Only no-auth pieces (forms, schedule, http, text-helper, store, date-helper, webhook, code), so no step shows a
missing-connection warning. Submits the lead form a few times so Runs has history."""
import json, sys, time, urllib.request, urllib.error
vars_path, url = sys.argv[1], sys.argv[2].rstrip('/')
V = {v['name']: v['value'] for v in json.load(open(vars_path))['vars']}
API = url + '/api/v1'

def rq(m, p, b=None, t=None):
    r = urllib.request.Request(API + p, data=json.dumps(b).encode() if b is not None else None, method=m,
                               headers={'content-type': 'application/json', 'user-agent': 'stackblaze-seed',
                                        **({'authorization': 'Bearer ' + t} if t else {})})
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            body = resp.read()
            return json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        raise SystemExit(f'{m} {p} -> {e.code} {e.read()[:300]}')

a = rq('POST', '/authentication/sign-in', {'email': V['ADMIN_EMAIL'], 'password': V['ADMIN_PASSWORD']})
T, PID = a['token'], a['projectId']
ver = {n: rq('GET', f'/pieces/@activepieces/piece-{n}', t=T)['version']
       for n in ['forms', 'schedule', 'http', 'text-helper', 'store', 'date-helper', 'webhook']}

def piece(kind, name, display, pc, op, inp, nxt=None):
    s = {'type': kind, 'name': name, 'displayName': display, 'valid': True,
         'settings': {'pieceName': f'@activepieces/piece-{pc}', 'pieceVersion': ver[pc],
                      ('triggerName' if kind == 'PIECE_TRIGGER' else 'actionName'): op,
                      'input': inp, 'propertySettings': {}}}
    if kind != 'PIECE_TRIGGER':
        s['skip'] = False
        s['settings']['errorHandlingOptions'] = {'continueOnFailure': {'value': False}, 'retryOnFailure': {'value': False}}
    if nxt:
        s['nextAction'] = nxt
    return s

def code(name, display, src, inp, nxt=None):
    s = {'type': 'CODE', 'name': name, 'displayName': display, 'valid': True, 'skip': False,
         'settings': {'input': inp, 'sourceCode': {'code': src, 'packageJson': '{}'},
                      'errorHandlingOptions': {'continueOnFailure': {'value': False}, 'retryOnFailure': {'value': False}}}}
    if nxt:
        s['nextAction'] = nxt
    return s

SCORE = '''export const code = async (inputs) => {
  const domain = String(inputs.email || '').split('@')[1] || '';
  const freeMail = ['gmail.com', 'outlook.com', 'yahoo.com', 'hotmail.com'].includes(domain);
  const size = Number(inputs.teamSize || 0);
  const score = (freeMail ? 10 : 40) + Math.min(size, 200) / 4;
  return { company: inputs.company, domain, score: Math.round(score), tier: score >= 60 ? 'hot' : score >= 35 ? 'warm' : 'cold' };
};'''
RATES = '''export const code = async (inputs) => {
  const rates = inputs.rates || {};
  const pick = ['USD', 'GBP', 'CHF', 'JPY', 'CAD'];
  const lines = pick.filter((c) => rates[c]).map((c) => `1 EUR = ${Number(rates[c]).toFixed(4)} ${c}`);
  return { date: inputs.date, summary: lines.join('\\n'), count: lines.length };
};'''
ORDER = '''export const code = async (inputs) => {
  const items = Array.isArray(inputs.items) ? inputs.items : [];
  const total = items.reduce((sum, it) => sum + Number(it.price || 0) * Number(it.qty || 1), 0);
  return { orderId: inputs.orderId, items: items.length, total: Math.round(total * 100) / 100, priority: total > 500 };
};'''

FLOWS = {
    'Lead intake: score and store': piece('PIECE_TRIGGER', 'trigger', 'Website lead form', 'forms', 'form_submission', {
        'waitForResponse': False,
        'inputs': [{'displayName': 'Name', 'type': 'text', 'description': '', 'required': True},
                   {'displayName': 'Email', 'type': 'text', 'description': '', 'required': True},
                   {'displayName': 'Company', 'type': 'text', 'description': '', 'required': True},
                   {'displayName': 'Seats', 'type': 'text', 'description': '', 'required': False}]},
        code('step_1', 'Score the lead', SCORE, {'email': '{{trigger.email}}', 'company': '{{trigger.company}}',
                                                  'teamSize': '{{trigger.seats}}'},
             piece('PIECE', 'step_2', 'Build the summary', 'text-helper', 'concat', {
                 'texts': ['{{trigger.name}} at {{step_1.company}}', 'score {{step_1.score}} ({{step_1.tier}})'], 'separator': ', '},
                 piece('PIECE', 'step_3', 'Add to the leads list', 'store', 'add_to_list', {
                     'key': 'leads', 'value': ['{{step_2}}'], 'ignore_if_exists': True, 'store_scope': 'COLLECTION'})))),
    'Daily exchange-rate digest': piece('PIECE_TRIGGER', 'trigger', 'Every weekday at 8:00', 'schedule', 'every_day', {
        'hour_of_the_day': 8, 'timezone': 'Europe/Berlin', 'run_on_weekends': False},
        piece('PIECE', 'step_1', 'Fetch EUR rates', 'http', 'send_request', {
            'method': 'GET', 'url': 'https://open.er-api.com/v6/latest/EUR', 'headers': {}, 'queryParams': {},
            'authType': 'NONE', 'authFields': {}, 'body_type': 'none', 'body': {}, 'failsafe': False},
            code('step_2', 'Format the digest', RATES, {'rates': '{{step_1.body.rates}}', 'date': '{{step_1.body.time_last_update_utc}}'},
                 piece('PIECE', 'step_3', 'Save the latest digest', 'store', 'put', {
                     'key': 'eur-digest', 'value': '{{step_2.summary}}', 'store_scope': 'COLLECTION'})))),
    'Shop order webhook': piece('PIECE_TRIGGER', 'trigger', 'New order (webhook)', 'webhook', 'catch_webhook', {'authType': 'none'},
        code('step_1', 'Total the order', ORDER, {'orderId': '{{trigger.body.orderId}}', 'items': '{{trigger.body.items}}'},
             piece('PIECE', 'step_2', 'Stamp the order date', 'date-helper', 'get_current_date', {
                 'timeFormat': 'YYYY-MM-DD HH:mm', 'timeZone': 'UTC'},
                 piece('PIECE', 'step_3', 'Keep the last order', 'store', 'put', {
                     'key': 'last-order', 'value': '{{step_1.orderId}}: {{step_1.total}} EUR at {{step_2}}', 'store_scope': 'COLLECTION'})))),
}

existing = {f['version']['displayName']: f for f in rq('GET', f'/flows?projectId={PID}&limit=100', t=T)['data']}
ids = {}
for name, trig in FLOWS.items():
    f = existing.get(name) or rq('POST', '/flows', {'displayName': name, 'projectId': PID}, t=T)
    rq('POST', f'/flows/{f["id"]}', {'type': 'IMPORT_FLOW', 'request': {'displayName': name, 'trigger': trig,
                                                                       'schemaVersion': None, 'notes': None}}, t=T)
    rq('POST', f'/flows/{f["id"]}', {'type': 'LOCK_AND_PUBLISH', 'request': {}}, t=T)
    ids[name] = f['id']
    print('flow', name, f['id'])
time.sleep(8)
leads = [('Maya Lindqvist', 'maya@northwind-labs.io', 'Northwind Labs', '120'), ('Jonas Weber', 'jonas.weber@gmail.com', 'Weber Design', '3'),
         ('Priya Raman', 'priya@quantaledger.com', 'Quanta Ledger', '45'), ('Tomás Ortega', 'tomas@ortega-freight.es', 'Ortega Freight', '260')]
for n, e, c, s in leads:
    rq('POST', f'/webhooks/{ids["Lead intake: score and store"]}', {'name': n, 'email': e, 'company': c, 'seats': s})
for oid, items in [('A-1042', [{'sku': 'desk', 'price': 349, 'qty': 2}, {'sku': 'lamp', 'price': 59, 'qty': 1}]),
                   ('A-1043', [{'sku': 'chair', 'price': 189, 'qty': 1}])]:
    rq('POST', f'/webhooks/{ids["Shop order webhook"]}', {'orderId': oid, 'items': items})
time.sleep(20)
runs = rq('GET', f'/flow-runs?projectId={PID}&limit=50', t=T)['data']
print('runs', len(runs), sorted({r['status'] for r in runs}))
json.dump(ids, open(vars_path + '.seed', 'w'))

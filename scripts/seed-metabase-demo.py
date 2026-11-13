#!/usr/bin/env python3
"""Seed a fresh Metabase deploy (services/metabase) for screenshots.

Uses only upstream's own sample content (MB_LOAD_SAMPLE_CONTENT: the Sample
Database and the "Examples" collection with the E-commerce Insights
dashboard) and adds two questions of our own on the Sample Database:
  - "Revenue by category per quarter" (query builder, stacked bar)
  - "Top products by revenue" (native SQL, table)
Both go into "Our analytics". Prints the new question ids as JSON.

Usage: MB_URL=https://... MB_EMAIL=... MB_PASSWORD=... python3 seed-metabase-demo.py
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

URL = os.environ['MB_URL'].rstrip('/')
session = None


def api(method, path, body=None):
    headers = {'Content-Type': 'application/json'}
    if session:
        headers['X-Metabase-Session'] = session
    req = urllib.request.Request(URL + path, method=method, headers=headers,
                                 data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f'{method} {path}: {e.code} {e.read()[:300]!r}')


session = api('POST', '/api/session', {'username': os.environ['MB_EMAIL'], 'password': os.environ['MB_PASSWORD']})['id']
sample = next(d for d in api('GET', '/api/database')['data'] if d.get('is_sample'))
for _ in range(60):
    tables = {t['name']: t for t in api('GET', f"/api/database/{sample['id']}/metadata")['tables']}
    if {'ORDERS', 'PRODUCTS'} <= tables.keys():
        break
    time.sleep(5)
orders, products = tables['ORDERS'], tables['PRODUCTS']
f = {(t['name'], fl['name']): fl['id'] for t in (orders, products) for fl in t['fields']}

existing = {c['name']: c['id'] for c in api('GET', '/api/card')}
out = {}

name = 'Revenue by category per quarter'
if name not in existing:
    q = {'database': sample['id'], 'type': 'query', 'query': {
        'source-table': orders['id'],
        'aggregation': [['sum', ['field', f[('ORDERS', 'TOTAL')], None]]],
        'breakout': [['field', f[('ORDERS', 'CREATED_AT')], {'temporal-unit': 'quarter'}],
                     ['field', f[('PRODUCTS', 'CATEGORY')], {'source-field': f[('ORDERS', 'PRODUCT_ID')]}]],
        'filter': ['time-interval', ['field', f[('ORDERS', 'CREATED_AT')], None], -8, 'quarter']}}
    existing[name] = api('POST', '/api/card', {
        'name': name, 'type': 'question', 'display': 'bar', 'dataset_query': q,
        'description': 'Order totals per product category, last eight quarters.',
        'visualization_settings': {'stackable.stack_type': 'stacked', 'graph.dimensions': ['CREATED_AT', 'CATEGORY'],
                                   'graph.metrics': ['sum']}})['id']
out['builder'] = existing[name]

name = 'Top products by revenue'
if name not in existing:
    sql = """SELECT p.TITLE AS product,
       p.CATEGORY AS category,
       COUNT(*) AS orders,
       ROUND(SUM(o.TOTAL), 2) AS revenue
FROM ORDERS o
JOIN PRODUCTS p ON p.ID = o.PRODUCT_ID
GROUP BY p.TITLE, p.CATEGORY
ORDER BY revenue DESC
LIMIT 20"""
    existing[name] = api('POST', '/api/card', {
        'name': name, 'type': 'question', 'display': 'table', 'visualization_settings': {},
        'dataset_query': {'database': sample['id'], 'type': 'native', 'native': {'query': sql}}})['id']
out['sql'] = existing[name]
out['dashboard'] = next(d['id'] for d in api('GET', '/api/dashboard') if d['name'] == 'E-commerce Insights')
print(json.dumps(out))

#!/usr/bin/env python3
"""Seed a Strapi template deploy with demo content for screenshots.

Usage: STRAPI_ADMIN_EMAIL=... STRAPI_ADMIN_PASSWORD=... python3 seed-strapi-demo.py <url>

Uses the template's own model (create-strapi-app --example: Article, Author,
Category, Global, About) and Strapi's example images at the pinned tag (no portrait
photos). Names and copy are invented. Registers the first admin if there is none. One admin
login per run (Strapi rate-limits /admin/login).
"""
import json, os, sys, urllib.request, urllib.error, uuid

URL = sys.argv[1].rstrip('/')
EMAIL = os.environ['STRAPI_ADMIN_EMAIL']; PW = os.environ['STRAPI_ADMIN_PASSWORD']
IMG = 'https://raw.githubusercontent.com/strapi/strapi/v5.62.0/packages/cli/create-strapi-app/templates/example/data/uploads/'


def req(method, path, body=None, token=None, raw=None, ctype='application/json'):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    r = urllib.request.Request(URL + path, data=data, method=method)
    if data is not None:
        r.add_header('Content-Type', ctype)
    if token:
        r.add_header('Authorization', 'Bearer ' + token)
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            t = resp.read()
            return resp.status, (json.loads(t) if t else None)
    except urllib.error.HTTPError as e:
        t = e.read()
        try:
            return e.code, json.loads(t)
        except Exception:
            return e.code, t


def must(res, what):
    s, b = res
    if s not in (200, 201):
        sys.exit(f'{what}: HTTP {s} {b}')
    return b


s, b = req('GET', '/admin/init')
if not b['data']['hasAdmin']:
    must(req('POST', '/admin/register-admin', {'firstname': 'Maya', 'lastname': 'Okafor', 'email': EMAIL, 'password': PW}), 'register')
tok = must(req('POST', '/admin/login', {'email': EMAIL, 'password': PW}), 'login')['data']['token']


def upload(fname, alt):
    with urllib.request.urlopen(IMG + fname, timeout=60) as r:
        data = r.read()
    bnd = uuid.uuid4().hex
    name = alt.lower().replace(' ', '-').replace('&', 'and') + '.jpg'
    info = json.dumps({'alternativeText': alt, 'name': name})
    body = (f'--{bnd}\r\nContent-Disposition: form-data; name="fileInfo"\r\n\r\n{info}\r\n'.encode()
            + f'--{bnd}\r\nContent-Disposition: form-data; name="files"; filename="{name}"\r\nContent-Type: image/jpeg\r\n\r\n'.encode()
            + data + f'\r\n--{bnd}--\r\n'.encode())
    return must(req('POST', '/upload', raw=body, token=tok, ctype='multipart/form-data; boundary=' + bnd), 'upload ' + fname)[0]['id']


CM = '/content-manager/collection-types/'


def create(uid, data, publish=True):
    d = must(req('POST', CM + uid, data, token=tok), 'create ' + uid)['data']
    if publish:
        must(req('POST', f'{CM}{uid}/{d["documentId"]}/actions/publish', {}, token=tok), 'publish ' + uid)
    return d


def get_or_create(uid, key, data, publish=True):
    s, b = req('GET', f'{CM}{uid}?pageSize=100', token=tok)
    for d in (b or {}).get('results', []):
        if d.get(key) == data[key]:
            return d
    return create(uid, data, publish)


rel = lambda d: {'connect': [{'documentId': d['documentId']}]}

cats = {n: get_or_create('api::category.category', 'name', {'name': n, 'slug': n, 'description': f'Posts about {n}'}, False) for n in ['news', 'food', 'nature', 'story', 'tech']}
maya = get_or_create('api::author.author', 'name', {'name': 'Maya Okafor', 'email': 'maya@harborpine.example'}, False)
jonas = get_or_create('api::author.author', 'name', {'name': 'Jonas Berg', 'email': 'jonas@harborpine.example'}, False)

TEXT = ('Every batch starts with a cupping table and a notebook. We taste the green coffee at three roast levels, '
        'write down what we find, and pick the profile that keeps the fruit without losing the sweetness.\n\n'
        '## What changes in the roaster\n\nCharge temperature, airflow and the time between first crack and drop. '
        'Small moves, big differences in the cup.')
ARTICLES = [
    ('How we roast a light espresso', 'Charge temperature, airflow and timing behind our new house espresso.', 'food', maya, 'coffee-beans.jpg', True),
    ('Latte art in five steps', 'Milk texture first, then the pour. A short guide from our baristas.', 'food', jonas, 'coffee-art.jpg', True),
    ('Afternoon light in the roastery', 'A quiet hour between the morning rush and the last roast of the day.', 'story', maya, 'coffee-shadow.jpg', True),
    ('Pizza night with the bakery next door', 'Our neighbours fired the oven and we brought cold brew.', 'news', jonas, 'we-love-pizza.jpg', True),
    ('Field notes from the coast', 'Where our spring blend got its name, and the walk that inspired it.', 'nature', maya, 'beautiful-picture.jpg', True),
    ('Shipping our subscription app', 'Behind the scenes of the app that sends a fresh bag every two weeks.', 'tech', jonas, 'a-bug-is-becoming-a-meme-on-the-internet.jpg', False),
]
for title, desc, cat, author, img, pub in ARTICLES:
    slug = title.lower().replace(' ', '-')
    create('api::article.article', {
        'title': title, 'slug': slug, 'description': desc[:80],
        'cover': upload(img, title), 'author': rel(author), 'category': rel(cats[cat]),
        'blocks': [
            {'__component': 'shared.rich-text', 'body': TEXT},
            {'__component': 'shared.quote', 'title': author['name'], 'body': 'Taste first, then decide.'},
        ],
    }, publish=pub)

ST = '/content-manager/single-types/'
for uid, data in [
    ('api::global.global', {'siteName': 'Harbor & Pine Journal', 'siteDescription': 'Stories from a small coffee roastery.',
                            'defaultSeo': {'metaTitle': 'Harbor & Pine Journal', 'metaDescription': 'Stories from a small coffee roastery.'}}),
    ('api::about.about', {'title': 'About Harbor & Pine', 'blocks': [{'__component': 'shared.rich-text', 'body': 'We roast small batches by the harbour and write about it here.'}]}),
]:
    must(req('PUT', ST + uid, data, token=tok), 'save ' + uid)  # no draft & publish on these
print('seeded', len(ARTICLES), 'articles')

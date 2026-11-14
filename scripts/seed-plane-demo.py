#!/usr/bin/env python3
"""Seed realistic demo content into the kept Plane deploy (workspace `plane`).

usage: seed-plane-demo.py <api vars.json> <proxy url>
(vars.json = `stackblaze variables list -p <project> -a <plane-api app> --reveal -o json`, chmod 600)

Adds a "Website Relaunch" project (WEB) with labels, ~16 work items across states and
priorities, a current cycle, a finished cycle, modules and a project page; and a smaller
"Mobile App" project. No personal data: the only member is the template's admin.
Also marks the admin's product tour done. Idempotent per project identifier (skips a project that already exists). Never prints secrets.
"""
import datetime as dt, json, os, sys
import http.cookiejar, urllib.parse, urllib.request, urllib.error


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


class Session:
    def __init__(self, base):
        self.base = base
        self.jar = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar), NoRedirect)

    def csrf(self):
        for c in self.jar:
            if c.name == 'csrftoken':
                return c.value
        return ''

    def req(self, method, path, body=None, form=None, raw=False, headers=None, url=None):
        h = {'Referer': self.base + '/', 'Origin': self.base}
        h.update(headers or {})
        data = None
        if form is not None:
            data = urllib.parse.urlencode(form).encode()
            h['Content-Type'] = 'application/x-www-form-urlencoded'
        elif body is not None:
            data = json.dumps(body).encode()
            h['Content-Type'] = 'application/json'
        if method not in ('GET', 'HEAD') and self.csrf():
            h['X-CSRFToken'] = self.csrf()
        r = urllib.request.Request(url or self.base + path, data=data, method=method, headers=h)
        try:
            resp = self.op.open(r, timeout=60)
            b = resp.read()
            return resp.status, b if raw else (json.loads(b) if b else None), dict(resp.headers)
        except urllib.error.HTTPError as e:
            b = e.read()
            try:
                return e.code, (b if raw else json.loads(b)), dict(e.headers)
            except Exception:
                return e.code, b[:300], dict(e.headers)

    def login(self, email, pw):
        self.req('GET', '/auth/get-csrf-token/')
        s, _, h = self.req('POST', '/auth/sign-in/', form={'csrfmiddlewaretoken': self.csrf(), 'email': email, 'password': pw})
        loc = {k.lower(): v for k, v in h.items()}.get('location', '')
        return s, loc



vars_path, base = sys.argv[1], sys.argv[2].rstrip('/')
v = {i['name']: i['value'] for i in json.load(open(vars_path))['vars']}
ss = Session(base)
s, loc = ss.login(v['ADMIN_EMAIL'], v['ADMIN_PASSWORD'])
assert s in (301, 302) and 'error' not in loc, ('login', s)
W = '/api/workspaces/plane'


def call(method, path, body=None, want=(200, 201, 204)):
    s, d, _ = ss.req(method, path, body=body)
    if s not in want:
        raise SystemExit(f'{method} {path} -> {s} {str(d)[:300]}')
    return d


me = call('GET', '/api/users/me/')
if not me.get('first_name') or me.get('first_name') == me.get('email', '').split('@')[0]:
    call('PATCH', '/api/users/me/', {'first_name': 'Alex', 'last_name': 'Morgan', 'display_name': 'alex'})
uid = me['id']
today = dt.date.today()
D = lambda n: (today + dt.timedelta(days=n)).isoformat()

existing = call('GET', f'{W}/projects/')
existing = existing if isinstance(existing, list) else existing.get('results', [])
idents = {p['identifier']: p for p in existing}


def project(name, ident, desc, emoji):
    if ident in idents:
        print('exists', ident)
        return None
    p = call('POST', f'{W}/projects/', {'name': name, 'identifier': ident, 'network': 2, 'description': desc,
                                         'logo_props': {'in_use': 'emoji', 'emoji': {'value': emoji}}})
    print('project', ident)
    return p['id']


def seed_project(pid, labels, items, cycles, modules, pages):
    P = f'{W}/projects/{pid}'
    # projects created through the API start with cycles, modules and views switched off
    call('PATCH', f'{P}/', {'cycle_view': True, 'module_view': True, 'page_view': True, 'issue_views_view': True})
    states = {st['name']: st['id'] for st in call('GET', f'{P}/states/')}
    lab = {}
    for n, c in labels:
        lab[n] = call('POST', f'{P}/issue-labels/', {'name': n, 'color': c})['id']
    ids = {}
    for it in items:
        name, state, prio, labs, assign, days, html = it
        body = {'name': name, 'state_id': states[state], 'priority': prio, 'label_ids': [lab[l] for l in labs],
                'assignee_ids': [uid] if assign else [], 'description_html': html or '<p></p>'}
        if days is not None:
            body['start_date'] = D(days[0]); body['target_date'] = D(days[1])
        ids[name] = call('POST', f'{P}/issues/', body)['id']
    for name, a, b, members in cycles:
        past = b < 0  # a finished cycle takes no items: create it current, add them, then move its dates
        c = call('POST', f'{P}/cycles/', {'name': name, 'start_date': D(0 if past else a), 'end_date': D(1 if past else b), 'project_id': pid})
        call('POST', f'{P}/cycles/{c["id"]}/cycle-issues/', {'issues': [ids[m] for m in members]})
        if past:
            call('PATCH', f'{P}/cycles/{c["id"]}/', {'start_date': D(a), 'end_date': D(b)})
    for name, status, a, b, desc, members in modules:
        m = call('POST', f'{P}/modules/', {'name': name, 'status': status, 'start_date': D(a), 'target_date': D(b),
                                            'description': desc})
        call('POST', f'{P}/modules/{m["id"]}/issues/', {'issues': [ids[x] for x in members]})
    for name, html in pages:
        call('POST', f'{P}/pages/', {'name': name, 'description_html': html, 'access': 0})
    print('seeded', len(ids), 'items')


WEB_ITEMS = [
    # name, state, priority, labels, assign me, (start, target) days from today, description
    ('Pick the new navigation structure', 'Done', 'high', ['Design'], True, (-24, -18), None),
    ('Write copy for the pricing page', 'Done', 'medium', ['Content'], False, (-20, -14), None),
    ('Set up preview deployments for every pull request', 'Done', 'medium', ['Engineering'], True, (-18, -12), None),
    ('Migrate blog posts to the new CMS', 'In Progress', 'high', ['Content', 'Engineering'], True, (-6, 4),
     '<p>Export the 140 published posts, keep their slugs and redirect the old URLs.</p>'),
    ('Build the responsive header and footer', 'Done', 'high', ['Engineering', 'Design'], True, (-5, 2), None),
    ('Image pipeline: AVIF with WebP fallback', 'In Progress', 'medium', ['Engineering', 'Performance'], False, (-3, 5), None),
    ('Accessibility pass on forms', 'In Progress', 'urgent', ['Engineering', 'Accessibility'], True, (-2, 3),
     '<p>Labels, focus order and error messages on the signup and contact forms.</p>'),
    ('Hero illustration, light and dark', 'Todo', 'medium', ['Design'], False, (1, 6), None),
    ('Add structured data to product pages', 'Todo', 'low', ['SEO'], False, (3, 9), None),
    ('Lighthouse budget in CI', 'Todo', 'high', ['Performance', 'Engineering'], True, (2, 8), None),
    ('Cookie banner with granular consent', 'Todo', 'urgent', ['Engineering'], False, (0, 4), None),
    ('Redirect map for retired URLs', 'Todo', 'medium', ['SEO'], True, (4, 10), None),
    ('Customer stories section', 'Backlog', 'low', ['Content'], False, None, None),
    ('Search across docs and blog', 'Backlog', 'medium', ['Engineering'], False, None, None),
    ('Localised landing pages (DE, FR)', 'Backlog', 'none', ['Content'], False, None, None),
    ('Status page link in the footer', 'Backlog', 'low', ['Design'], False, None, None),
]
WEB_LABELS = [('Design', '#8b5cf6'), ('Engineering', '#3b82f6'), ('Content', '#f59e0b'), ('SEO', '#10b981'),
              ('Performance', '#ef4444'), ('Accessibility', '#06b6d4')]
WEB_CYCLES = [
    ('Sprint 13', -28, -15, ['Pick the new navigation structure', 'Write copy for the pricing page',
                             'Set up preview deployments for every pull request']),
    ('Sprint 14', -7, 6, ['Migrate blog posts to the new CMS', 'Build the responsive header and footer',
                          'Image pipeline: AVIF with WebP fallback', 'Accessibility pass on forms',
                          'Hero illustration, light and dark', 'Lighthouse budget in CI',
                          'Cookie banner with granular consent', 'Redirect map for retired URLs']),
    ('Sprint 15', 7, 20, ['Add structured data to product pages', 'Search across docs and blog']),
]
WEB_MODULES = [
    ('Content migration', 'in-progress', -10, 12, 'Move every page and post to the new CMS without losing a URL.',
     ['Migrate blog posts to the new CMS', 'Redirect map for retired URLs', 'Write copy for the pricing page',
      'Customer stories section']),
    ('Performance', 'planned', -3, 15, 'Fast on a mid-range phone: LCP under 2 s.',
     ['Image pipeline: AVIF with WebP fallback', 'Lighthouse budget in CI']),
    ('Design system', 'in-progress', -25, 5, 'Header, footer, typography and colour tokens.',
     ['Pick the new navigation structure', 'Build the responsive header and footer', 'Hero illustration, light and dark']),
]
WEB_PAGES = [
    ('Launch plan', '<h2>Goal</h2><p>Relaunch the marketing site on the new CMS with no lost traffic.</p>'
                    '<h2>Milestones</h2><ul><li><p>Sprint 14: header, footer and blog migration</p></li>'
                    '<li><p>Sprint 15: structured data and search</p></li><li><p>Launch: redirects live, old site read-only</p></li></ul>'
                    '<h2>Risks</h2><p>Old URLs without a redirect. Mitigation: the redirect map is a launch blocker.</p>'),
    ('Content style guide', '<h2>Voice</h2><p>Plain, direct and friendly. Short sentences.</p>'
                            '<h2>Headlines</h2><p>Sentence case, no full stop.</p>'),
]

MOB_ITEMS = [
    ('Offline mode for the task list', 'In Progress', 'high', ['Feature'], True, (-4, 6), None),
    ('Push notifications for mentions', 'Todo', 'medium', ['Feature'], False, (2, 9), None),
    ('Crash on rotating the settings screen', 'In Progress', 'urgent', ['Bug'], True, (-1, 1), None),
    ('Dark mode icons', 'Done', 'low', ['Design'], False, (-12, -8), None),
    ('Release 2.4 to the stores', 'Todo', 'high', ['Release'], True, (5, 7), None),
    ('Biometric sign-in', 'Backlog', 'medium', ['Feature'], False, None, None),
]
MOB_LABELS = [('Feature', '#3b82f6'), ('Bug', '#ef4444'), ('Design', '#8b5cf6'), ('Release', '#10b981')]

pid = project('Website Relaunch', 'WEB', 'The new marketing site: CMS migration, design system and performance.', '🚀')
if pid:
    seed_project(pid, WEB_LABELS, WEB_ITEMS, WEB_CYCLES, WEB_MODULES, WEB_PAGES)
pid = project('Mobile App', 'MOB', 'iOS and Android app, release 2.4.', '📱')
if pid:
    seed_project(pid, MOB_LABELS, MOB_ITEMS, [('Release 2.4', -6, 7, [i[0] for i in MOB_ITEMS[:5]])], [], [])
call('PATCH', '/api/users/me/tour-completed/', {})
print('done')

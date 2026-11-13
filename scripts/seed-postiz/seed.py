#!/usr/bin/env python3
"""seed.py <vars.json> <url> <wp-creds.json> <imgdir>
Demo content for screenshots: the WordPress channel (a blog we own), a week of
scheduled posts with images, two posts published now. Invented brand only."""
import base64, json, os, sys, datetime as dt
import requests

vars_path, base, wp_path, imgdir = sys.argv[1:5]
base = base.rstrip('/')
v = {r['name']: r['value'] for r in json.load(open(vars_path))['vars']}
wp = json.load(open(wp_path))
s = requests.Session()
r = s.post(base + '/api/auth/login', json={'email': v['POSTIZ_ADMIN_EMAIL'], 'password': v['POSTIZ_ADMIN_PASSWORD'], 'provider': 'LOCAL'})
r.raise_for_status()
s.post(base + '/api/user/personal', json={'fullname': 'Maya Okafor', 'bio': 'Social lead, Northwind Coffee'})

# Remove earlier pass-bar posts.
frm = (dt.datetime.utcnow() - dt.timedelta(days=40)).isoformat() + 'Z'
to = (dt.datetime.utcnow() + dt.timedelta(days=40)).isoformat() + 'Z'
for p in s.get(base + '/api/posts', params={'startDate': frm, 'endDate': to}).json().get('p', []):
    s.delete(base + f"/api/posts/{p['g']}")

# (Re)connect the channel so it picks up the blog's display name.
state = s.get(base + '/api/integrations/social/wordpress').json()['url']
code = base64.b64encode(json.dumps({'domain': wp['url'], 'username': wp['user'], 'password': wp['app_password']}).encode()).decode()
r = s.post(base + '/api/integrations/social-connect/wordpress', json={'state': state, 'code': code, 'timezone': 'UTC'})
r.raise_for_status()
cid = r.json()['id']
print('channel', r.json().get('name'))
s.put(base + f"/api/integrations/{cid}/custom-name", json={"name": "Northwind Coffee Journal"})

media = {}
for f in sorted(os.listdir(imgdir)):
    with open(os.path.join(imgdir, f), 'rb') as fh:
        r = s.post(base + '/api/media/upload-simple', files={'file': (f, fh, 'image/png')})
    r.raise_for_status()
    media[f.split('.')[0]] = r.json()['path']
    # Save it in the media library too, like an upload from the composer.
    s.post(base + '/api/media/save-media', json={'name': f, 'path': r.json()['path'], 'originalName': f})

today = dt.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
POSTS = [
    # (day offset, hour, minute, title, body, image)
    (1, 9, 0, 'Autumn Blend is back', 'Maple, toasted pecan and dark cocoa. Our Autumn Blend returns to every shop this weekend, and bags ship from Monday.', 'autumn'),
    (3, 8, 30, 'Oat Latte Week starts today', 'Every oat latte is $1 off, Monday to Friday. Bring a friend who has never tried one.', 'latte'),
    (4, 12, 0, 'How we pick a single origin', 'Three cuppings, two roast profiles, one decision. A look at how Colombia Huila made the menu.', 'beans'),
    (6, 15, 0, 'Roasting day: Ethiopia Guji', 'Fresh light roast on Thursday. Floral, bright, and best as a pour-over. Pre-order for pickup.', 'roast'),
    (8, 10, 0, 'Pour-over 101 this Saturday', 'A free 45-minute class at the Harbor Street shop. Cups, kettles and beans on us. Ten seats left.', 'brew'),
    (10, 9, 0, 'Holiday gift boxes', 'Three bags, one tasting card, wrapped by the team. Order by December 10 for delivery before the holidays.', None),
    (12, 17, 30, 'Meet the night shift', 'Our late baristas share their favorite after-dark drinks. Hint: there is a cold brew tonic involved.', None),
    (15, 11, 0, 'Colombia Huila, now in bags', 'Red apple, caramel and a clean finish. 250 g and 1 kg bags in every shop and online.', 'beans'),
]
for off, h, m, title, body, img in POSTS:
    when = (today + dt.timedelta(days=off, hours=h, minutes=m)).isoformat() + 'Z'
    settings = {'__type': 'wordpress', 'title': title, 'type': 'posts', 'status': 'publish'}
    if img:
        settings['main_image'] = {'id': img, 'path': media[img]}
    post = {'type': 'schedule', 'shortLink': False, 'date': when, 'tags': [],
            'posts': [{'integration': {'id': cid},
                       'value': [{'content': f'<p>{body}</p>', 'image': [{'id': img, 'path': media[img]}] if img else []}],
                       'settings': settings}]}
    r = s.post(base + '/api/posts', json=post)
    print('scheduled' if r.ok else f'FAILED {r.status_code} {r.text[:120]}', when, title)

# Two posts that go out now, so the calendar shows published ones too.
for title, body, img in [('Good morning from Harbor Street', 'Doors open at 7. The Autumn Blend is on drip all day.', 'autumn'),
                         ('This week on the bar', 'Oat lattes, Guji pour-overs and a new pastry from Lumen Bakery.', 'latte')]:
    post = {'type': 'now', 'shortLink': False, 'date': dt.datetime.utcnow().isoformat() + 'Z', 'tags': [],
            'posts': [{'integration': {'id': cid}, 'value': [{'content': f'<p>{body}</p>', 'image': []}],
                       'settings': {'__type': 'wordpress', 'title': title, 'type': 'posts', 'status': 'publish',
                                    'main_image': {'id': img, 'path': media[img]}}}]}
    r = s.post(base + '/api/posts', json=post)
    print('now' if r.ok else f'FAILED {r.status_code} {r.text[:120]}', title)

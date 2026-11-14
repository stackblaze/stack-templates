#!/usr/bin/env python3
"""Seed a Chatwoot account with realistic support data.  seed.py <url>

Customer messages go through the real web-widget API (incoming); agent replies,
labels, notes and statuses through the account API. Admin creds from CW_EMAIL /
CW_PASSWORD. Names are invented.
"""
import os, re, sys, time
import requests

U = sys.argv[1].rstrip('/')
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'}
me = requests.post(U + '/auth/sign_in', json={'email': os.environ['CW_EMAIL'], 'password': os.environ['CW_PASSWORD']}).json()['data']
H = {'api_access_token': me['access_token']}
A = '%s/api/v1/accounts/%s' % (U, me['account_id'])


def j(r):
    if not r.ok:
        raise SystemExit('%s %s: %s' % (r.request.method, r.url, r.text[:300]))
    return r.json()


# account basics: finish the post-signup "account details" step the way its form does
r = requests.patch(A + '/onboarding', headers=H, json={'onboarding_step': 'account_details', 'name': 'Northwind Outfitters',
    'locale': 'en', 'timezone': 'America/New_York', 'industry': 'E-commerce', 'company_size': '11-50', 'user_role': 'Support',
    'website': 'northwind.example', 'referral_source': 'Other'})
print('onboarding step', r.status_code)
j(requests.patch(A, headers=H, json={'name': 'Northwind Outfitters'}))
for t, c, d in [('order-status', '#1F93FF', 'Where is my order'), ('returns', '#F5A524', 'Returns and exchanges'),
                ('billing', '#E5484D', 'Invoices and payments'), ('vip', '#8E4EC6', 'Priority customers'),
                ('product-question', '#30A46C', 'Sizing and product details')]:
    requests.post(A + '/labels', headers=H, json={'title': t, 'color': c, 'description': d, 'show_on_sidebar': True})
for code, text in [('shipping', 'Orders ship within 1 business day. You will get a tracking link by email as soon as it leaves our warehouse.'),
                   ('returns', 'You can return unworn items within 30 days. Start a return at northwind.example/returns and we will email a prepaid label.'),
                   ('thanks', 'Thanks for reaching out! Is there anything else I can help with today?')]:
    requests.post(A + '/canned_responses', headers=H, json={'short_code': code, 'content': text})
teams = j(requests.get(A + '/teams', headers=H))
team = next((t for t in teams if t['name'] == 'support'), None) or j(requests.post(A + '/teams', headers=H, json={'name': 'Support', 'description': 'Customer support'}))

inboxes = j(requests.get(A + '/inboxes', headers=H))['payload']
web = next((i for i in inboxes if i['channel_type'] == 'Channel::WebWidget'), None)
if not web:
    web = j(requests.post(A + '/inboxes', headers=H, json={'name': 'Website', 'greeting_enabled': True,
        'greeting_message': 'Hi! How can we help?', 'channel': {'type': 'web_widget', 'website_url': 'https://northwind.example',
        'widget_color': '#1f93ff', 'welcome_title': 'Hi there!', 'welcome_tagline': 'We usually reply in a few minutes.'}}))
    requests.post(A + '/inbox_members', headers=H, json={'inbox_id': web['id'], 'user_ids': [me['id']]})
TOKEN = web['website_token']
api_inbox = next((i for i in inboxes if i['channel_type'] == 'Channel::Api'), None) or j(requests.post(A + '/inboxes', headers=H, json={
    'name': 'Mobile app', 'channel': {'type': 'api', 'webhook_url': ''}}))
requests.post(A + '/inbox_members', headers=H, json={'inbox_id': api_inbox['id'], 'user_ids': [me['id']]})

# (customer, email, city, [(who, text)], labels, status, note)
CONVS = [
    ('Maya Lindqvist', 'maya.lindqvist@example.com', 'Stockholm',
     [('c', 'Hi! I ordered the Ridge 40L backpack on Monday (order #4821) and it still says processing. Any update?'),
      ('a', 'Hi Maya, thanks for your patience! I checked #4821: it was packed this morning and ships today. You will get the tracking link by email within a few hours.'),
      ('c', 'Perfect, thank you so much!')], ['order-status'], 'resolved', None),
    ('Omar Haddad', 'omar.haddad@example.com', 'Toronto',
     [('c', 'The trail runners I got are half a size too small. Can I swap them for a 10.5?'),
      ('a', 'Of course! Exchanges are free within 30 days. I have started one for you: a prepaid label is on its way to omar.haddad@example.com.'),
      ('c', 'Great. Do I need to include the original box?')], ['returns'], 'open', 'Customer is a repeat buyer, 6 orders this year.'),
    ('Priya Nair', 'priya.nair@example.com', 'Bengaluru',
     [('c', 'Is the Summit down jacket warm enough for -15°C? I am trying to decide between it and the parka.'),
      ('a', 'Good question! The Summit is rated to about -10°C on its own. For -15°C with wind, the Glacier parka is the better pick.')], ['product-question'], 'open', None),
    ('Lucas Moreau', 'lucas.moreau@example.com', 'Lyon',
     [('c', 'I was charged twice for order #4790. Can you refund the duplicate?')], ['billing', 'vip'], 'open', 'Verify the second charge in Stripe before refunding.'),
    ('Hannah Becker', 'hannah.becker@example.com', 'Munich',
     [('c', 'Do you ship to Austria? I could not find it in the checkout list.'),
      ('a', 'We do! Austria was missing from the list this morning; it is back now. Shipping takes 3 to 5 business days.')], ['order-status'], 'pending', None),
    ('Kenji Watanabe', 'kenji.watanabe@example.com', 'Osaka',
     [('c', 'Hello, can I still change the color on my order? I picked green but want navy.')], [], 'open', None),
]

def widget_conv(name, email, city, first):
    s = requests.Session(); s.headers.update(UA)
    h = s.get(U + '/widget', params={'website_token': TOKEN}).text
    tok = re.search(r"window\.authToken = '([^']+)'", h).group(1)
    r = j(s.post(U + '/api/v1/widget/conversations', params={'website_token': TOKEN}, headers={'X-Auth-Token': tok},
                 json={'contact': {'name': name, 'email': email}, 'message': {'content': first, 'referer_url': 'https://northwind.example/orders'}}))
    return s, tok, r['id']


import os as _os
if _os.environ.get('ONLY_ONBOARD'): raise SystemExit(0)
for name, email, city, msgs, labels, status, note in CONVS:
    s, tok, conv_display = widget_conv(name, email, city, msgs[0][1])
    time.sleep(0.5)
    convs = j(requests.get(A + '/conversations', headers=H, params={'status': 'all', 'q': ''}))['data']['payload']
    conv = next(c for c in convs if c['meta']['sender']['email'] == email)
    cid = conv['id']
    requests.patch('%s/contacts/%s' % (A, conv['meta']['sender']['id']), headers=H,
                   json={'additional_attributes': {'city': city, 'company_name': ''}})
    for who, text in msgs[1:]:
        time.sleep(0.6)
        if who == 'a':
            j(requests.post('%s/conversations/%s/messages' % (A, cid), headers=H, json={'content': text, 'message_type': 'outgoing'}))
        else:
            j(s.post(U + '/api/v1/widget/messages', params={'website_token': TOKEN}, headers={'X-Auth-Token': tok}, json={'message': {'content': text}}))
    if note:
        j(requests.post('%s/conversations/%s/messages' % (A, cid), headers=H, json={'content': note, 'private': True}))
    if labels:
        j(requests.post('%s/conversations/%s/labels' % (A, cid), headers=H, json={'labels': labels}))
    requests.post('%s/conversations/%s/assignments' % (A, cid), headers=H, json={'assignee_id': me['id']})
    if status != 'open':
        j(requests.post('%s/conversations/%s/toggle_status' % (A, cid), headers=H, json={'status': status}))
    print('seeded', name, cid)
print('done')

import json
import re
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
index = json.loads((ROOT / "index.json").read_text(encoding="utf-8"))

catalog_path = os.path.join(os.environ["TEMP"], "elest-catalog.html")
content = open(catalog_path, encoding="utf-8", errors="ignore").read()
apps = [
    t
    for t in json.loads(re.search(r"var fullResponse = (\[.*?\]);", content).group(1))[0]["templates"]
    if t["category"] == "Applications"
]

BATCH1 = {
    "nextcloud", "immich", "chatwoot", "typebot", "plausible", "plane",
    "discourse", "infisical", "linkwarden", "penpot",
}
BATCH2 = {
    "jellyfin", "formbricks", "openproject", "matomo", "mealie", "nodebb",
    "syncthing", "hedgedoc", "freshrss", "vikunja",
}
MANUAL = {
    "wordpress": "wordpress", "wordpressmultisites": "wordpress", "ghost": "ghost",
    "metabase": "metabase", "metabasepostgres": "metabase", "vaultwarden": "vaultwarden",
    "bookstack": "bookstack", "outline": "outline", "twenty": "twenty",
    "activepieces": "activepieces", "affine": "affine", "archivebox": "archivebox",
    "cal": "calcom", "changedetection": "changedetection", "corteza": "corteza",
    "dashy": "dashy", "docmost": "docmost", "docuseal": "docuseal", "etherpad": "etherpad",
    "fider": "fider", "filestash": "filestash", "illa": "illa", "joomla": "joomla",
    "kener": "kener", "kimai": "kimai", "languagetool": "languagetool", "leantime": "leantime",
    "limesurvey": "limesurvey", "logto": "logto", "mattermostteamedition": "mattermost",
    "memos": "memos", "paperlessngx": "paperless-ngx", "peppermint": "peppermint",
    "postiz": "postiz", "rallly": "rallly", "rocketchat": "rocketchat", "searxng": "searxng",
    "serpbear": "serpbear", "stirlingpdf": "stirlingpdf", "tolgee": "tolgee", "traggo": "traggo",
    "trilium": "trilium", "umami": "umami", "wekan": "wekan", "wikijs": "wikijs",
    "nekorooms": "neko", "draw": "excalidraw", "penpot": "penpot-frontend",
    "mirotalk": "mirotalk-p2p", **{b: b for b in BATCH1 | BATCH2},
}


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


stack_map = {norm(s["name"]): s["name"] for s in index["services"]}
stack_map.update({norm(s.get("dirname", s["name"])): s["name"] for s in index["services"]})

missing = []
for e in apps:
    keys = [norm(e["title"]), norm(e.get("shortTitle", ""))]
    if any(k in MANUAL or k in stack_map for k in keys):
        continue
    missing.append(e)

title_by_norm = {norm(e["title"]): e for e in missing}
popular = sorted(
    [e for e in missing if e.get("isPopular")],
    key=lambda x: x.get("minRamGB") if isinstance(x.get("minRamGB"), (int, float)) and x.get("minRamGB") >= 0 else 99,
)

print("GAP: %d Elest apps still missing (of 211)" % len(missing))
print("Stack: %d templates, ~%d matched" % (len(index["services"]), 211 - len(missing)))
print()
print("BATCH 3 — TOP 10 (recommended)")
for i, slug in enumerate([
    "opnform", "netbox", "zulip", "appflowy", "zammad", "automatisch",
    "owntcast", "flarum", "kroki", "cryptpad",
], 1):
    e = title_by_norm.get(slug)
    if not e:
        print("  %2d. %s — NOT FOUND" % (i, slug))
        continue
    pop = " [Elest popular]" if e.get("isPopular") else ""
    ram = e.get("minRamGB")
    print("  %2d. %-18s %s ram=%s" % (i, e["title"], pop, ram))

print()
print("BATCH 3 — RUNNERS UP (11-20)")
for slug in [
    "grist", "focalboard", "xwiki", "joplin", "wazuh", "superset",
    "element", "authelia", "onlyoffice", "jitsi",
]:
    e = title_by_norm.get(slug)
    if e:
        pop = " [popular]" if e.get("isPopular") else ""
        print("  - %s%s (ram=%s)" % (e["title"], pop, e.get("minRamGB")))

print()
print("Elest popular still missing:")
for e in popular[:15]:
    print("  - %s (ram=%s)" % (e["title"], e.get("minRamGB")))

print()
print("SKIP — near duplicates already in stack")
nearby = {
    "posthog": "umami/metabase/plausible/matomo",
    "flarum": "discourse/nodebb",
    "phpbb": "discourse/nodebb",
    "zammad": "chatwoot/peppermint",
    "freescout": "chatwoot",
    "automatisch": "activepieces/n8n",
    "opnform": "limesurvey/typebot/formbricks",
    "focalboard": "wekan/plane",
    "grist": "nocodb",
}
for slug, note in nearby.items():
    if slug in title_by_norm:
        print("  %s — %s" % (title_by_norm[slug]["title"], note))

print()
print("DEFER — heavy / multi-service / niche")
for slug in [
    "posthog", "onlyoffice", "jitsi", "element", "odooerpcrm", "erpnext",
    "mastodon", "misskey", "woocommerce", "magento", "temporal", "authelia",
]:
    e = title_by_norm.get(slug)
    if e:
        print("  - %s (ram=%s)" % (e["title"], e.get("minRamGB")))

print()
print("ORPHAN SERVICES (in repo, not in index)")
indexed = {norm(s["name"]) for s in index["services"]}
for d in sorted(ROOT.glob("services/*/app.yaml")):
    name = d.parent.name
    n = norm(name)
    if n not in indexed and norm(name.replace("-", "")) not in indexed:
        print("  -", name)

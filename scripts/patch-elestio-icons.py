#!/usr/bin/env python3
"""Download Elestio icons and patch icon refs in specs, templates, and index.json."""
from __future__ import annotations
import io, json, re, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "services"
SPECS = Path(__file__).resolve().parent / "_specs"
BASE_RAW = "https://raw.githubusercontent.com/stackblaze/stack-templates/main/services"
ELESTIO_BASE = "https://dash.elest.io/templatesIcones"

# slug -> Elestio icon filename (without .png)
SLUG_TO_ELESTIO: dict[str, str] = {
    # ── New 138 templates ──────────────────────────────────────────────
    "akaunting":          "Akaunting",
    "attendize":          "Attendize",
    "audiomuse-ai":       "AudioMuse-AI",
    "authelia":           "Authelia",
    "automatisch":        "Automatisch",
    "azuracast":          "AzuraCast",
    "bigcapital":         "Bigcapital",
    "btcpay":             "BTCPay",
    "castopod":           "Castopod",
    "chiefonboarding":    "ChiefOnboarding",
    "civicrm":            "CiviCRM",
    "convex":             "Convex",
    "countly":            "Countly",
    "crater":             "Crater",
    "cryptgeon":          "Cryptgeon",
    "cryptomator":        "Cryptomator",
    "dittofeed":          "Dittofeed",
    "docassemble":        "Docassemble",
    "docspell":           "Docspell",
    "documize":           "Documize",
    "drawio":             "draw",
    "dremio":             "Dremio",
    "drupal":             "Drupal",
    "element":            "Element",
    "emqx":               "EMQX",
    "eneo":               "Eneo",
    "erpnext":            "ErpNext",
    "erugo":              "Erugo",
    "firefish":           "Firefish",
    "flarum":             "Flarum",
    "flatnotes":          "Flatnotes",
    "frappehr":           "FrappeHR",
    "freescout":          "FreeScout",
    "friendica":          "Friendica",
    "fugu":               "Fugu",
    "funkwhale":          "Funkwhale",
    "garage":             "Garage",
    "ghostfolio":         "Ghostfolio",
    "glean":              "Glean",
    "grist":              "Grist",
    "growchief":          "GrowChief",
    "hermes":             "Hermes",
    "hi-events":          "Hi-events",
    "hop":                "Hop",
    "hortusfox":          "HortusFox",
    "hyperswitch":        "Hyperswitch",
    "indico":             "Indico",
    "inventree":          "InvenTree",
    "invoiceninja":       "Invoice_Ninja",
    "iomad":              "ICMAD",
    "iris":               "IRIS",
    "itop":               "iTop",
    "jibri":              "Jibri",
    "jitsi":              "Jitsi",
    "joplin":             "Joplin",
    "kbin":               "KBIN",
    "keeweb":             "KeeWeb",
    "kener":              "Kener",
    "kroki":              "Kroki",
    "lago":               "Lago",
    "lemmy":              "Lemmy",
    "lightdash":          "Lightdash",
    "lightldap":          "LightLDAP",
    "lobsters":           "Lobsters",
    "magento":            "Magento",
    "mantisbt":           "MantisBT",
    "mapzy":              "Mapzy",
    "mastodon":           "Mastodon",
    "mautic":             "Mautic",
    "maybe":              "Maybe",
    "mediacms":           "MediaCMS",
    "metabase-postgres":  "MetabasePostgres",
    "metatrader5":        "MetaTrader5",
    "minthcm":            "MintHCM",
    "misskey":            "Misskey",
    "moodle":             "Moodle",
    "neko-rooms":         "Neko_Rooms",
    "nopcommerce":        "nopCommerce",
    "odoo":               "Odoo_ERP_CRM",
    "ojs":                "OJS",
    "omeka":              "Omeka",
    "onlyoffice":         "OnlyOffice",
    "openobserve":        "OpenObserve",
    "openslides":         "OpenSlides",
    "opnform":            "OpnForm",
    "ova-runner":         "OVA-Runner",
    "owncast":            "Owncast",
    "owncloud":           "ownCloud",
    "papercups":          "Papercups",
    "papermerge":         "Papermerge",
    "parseable":          "Parseable",
    "passit":             "Passit",
    "peertube":           "PeerTube",
    "penpot":             "Penpot",
    "photon":             "Photon",
    "photoprism":         "PhotoPrism",
    "phpbb":              "PhpBB",
    "picoshare":          "Picoshare",
    "piefed":             "PieFed",
    "pixelfed":           "Pixelfed",
    "pleroma":            "Pleroma",
    "posthog":            "PostHog",
    "prestashop":         "Prestashop",
    "pretix":             "Pretix",
    "pritunl":            "Pritunl",
    "pydio":              "Cells",
    "redash":             "Redash",
    "revolt":             "Revolt",
    "rustdesk":           "RustdeskServer",
    "rustfs":             "RustFS",
    "rybbit":             "Rybbit",
    "saleor":             "Saleor",
    "saltcorn":           "Saltcorn",
    "searxng":            "SearXNG",
    "seaweedfs":          "SeaweedFS",
    "sharkey":            "Sharkey",
    "shopware":           "Shopware",
    "snipe-it":           "Snipe-it",
    "suitecrm":           "SuiteCRM",
    "taiga":              "Taiga",
    "temporal":           "Temporal",
    "totaljs-flow":       "TotaljsFlow",
    "tracardi":           "Tracardi",
    "traduora":           "Traduora",
    "trudesk":            "Trudesk",
    "ubuntu-desktop":     "Ubuntu-Desktop",
    "unibee":             "UniBee",
    "unomi":              "Unomi",
    "uvdesk":             "UVdesk",
    "wazuh":              "Wazuh",
    "wger":               "Wger",
    "woocommerce":        "WooCommerce",
    "wordpress-multisite":"Wordpress-Multisites",
    "xwiki":              "XWiki",
    "yopass":             "Yopass",
    "yourls":             "YOURLS",
    "zammad":             "Zammad",
    # ── Pre-existing templates also in Elestio catalog ─────────────────
    "wordpress":          "Wordpress",
    "ghost":              "Ghost",
    "nextcloud":          "Nextcloud",
    "vaultwarden":        "Vaultwarden",
    "chatwoot":           "Chatwoot",
    "plausible":          "Plausible_Analytics",
    "mattermost":         "Mattermost_Team_Edition",
    "nodebb":             "NodeBB",
    "discourse":          "Discourse",
    "rocketchat":         "Rocket.Chat",
    "limesurvey":         "LimeSurvey",
    "umami":              "Umami",
    "cryptpad":           "CryptPad",
    "dolibarr":           "Dolibarr",
    "formbricks":         "Formbricks",
    "plane":              "Plane",
    "glpi":               "GLPI",
    "leantime":           "Leantime",
    "logto":              "Logto",
    "password-pusher":    "Password_Pusher",
    "humhub":             "HumHub",
    "easyappointments":   "EasyAppointments",
    "jellyfin":           "Jellyfin",
    "corteza":            "Corteza",
    "vikunja":            "Vikunja",
    "stirling-pdf":       "Stirling-PDF",
    "freshrss":           "FreshRSS",
    "linkwarden":         "Linkwarden",
    "tolgee":             "Tolgee",
    "peppermint":         "Peppermint",
    "joomla":             "Joomla",
    "docmost":            "Docmost",
    "appflowy":           "AppFlowy",
    "postiz":             "Postiz",
    "superset":           "Superset",
    "openproject":        "OpenProject",
    "syncthing":          "Syncthing",
    "filestash":          "Filestash",
    "outline":            "Outline",
    "kimai":              "Kimai",
    "bookstack":          "BookStack",
    "paperless-ngx":      "Paperless-ngx",
    "zulip":              "Zulip",
    "shlink":             "Shlink",
    "focalboard":         "FocalBoard",
    "hedgedoc":           "HedgeDoc",
    "archivebox":         "ArchiveBox",
    "fider":              "Fider",
    "etherpad":           "Etherpad",
    "mirotalk":           "MiroTalk",
    "wikijs":             "Wikijs",
    "matomo":             "Matomo",
    "metabase":           "Metabase",
    "changedetection":    "ChangeDetection",
    "typebot":            "Typebot",
    "memos":              "Memos",
    "wekan":              "Wekan",
    "immich":             "Immich",
    "serpbear":           "SerpBear",
    "activepieces":       "Activepieces",
    "expocrm":            "ExpoCRM",
    "affine":             "Affine",
    "rallly":             "Rallly",
    "trilium":            "Trilium",
    "meelie":             "Meelie",
    "traggo":             "Traggo",
    "infisical":          "Infisical",
    "illa":               "ILLA",
    "docuseal":           "DocuSeal",
    "twenty":             "Twenty",
    "cal":                "Cal",
    "languagetool":       "LanguageTool",
    "netbox":             "NetBox",
}

ICON_ANNOTATION = "kubero.dev/template.icon"


def download_icon(slug: str, elestio_name: str) -> str | None:
    """Download icon PNG; return final icon URL (raw GitHub) or None on error."""
    dest = SERVICES / slug / "icon.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    src_url = f"{ELESTIO_BASE}/{elestio_name}.png"
    try:
        req = urllib.request.Request(src_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
        dest.write_bytes(data)
        return f"{BASE_RAW}/{slug}/icon.png"
    except Exception as exc:
        print(f"  WARN download failed {slug} ({src_url}): {exc}")
        return None


def patch_yaml_icon(path: Path, new_url: str) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    pat = re.compile(
        r"(    " + re.escape(ICON_ANNOTATION) + r": ).*"
    )
    new_text = pat.sub(r"\g<1>" + new_url, text)
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False


def patch_spec_icon(slug: str, new_url: str) -> bool:
    p = SPECS / f"{slug}.json"
    if not p.exists():
        return False
    d = json.loads(p.read_text(encoding="utf-8"))
    d["icon"] = new_url
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def patch_index_icon(data: dict, slug: str, new_url: str) -> bool:
    for svc in data.get("services", []):
        if svc.get("name") == slug or svc.get("dirname") == slug:
            svc["icon"] = new_url
            return True
    return False


def main() -> int:
    index_path = ROOT / "index.json"
    index_data = json.loads(index_path.read_text(encoding="utf-8"))

    downloaded = 0
    skipped = 0
    yaml_patched = 0
    spec_patched = 0
    index_patched = 0

    for slug, elestio_name in sorted(SLUG_TO_ELESTIO.items()):
        svc_dir = SERVICES / slug
        if not svc_dir.exists():
            print(f"  skip {slug}: services/ dir not found")
            skipped += 1
            continue

        print(f"  {slug} <- {elestio_name}.png", end=" ")
        new_url = download_icon(slug, elestio_name)
        if not new_url:
            print("[SKIP]")
            skipped += 1
            continue
        downloaded += 1
        print("[DL]")

        # patch spec JSON
        if patch_spec_icon(slug, new_url):
            spec_patched += 1

        # patch YAML templates
        for fname in ("app.yaml", "app.ha.yaml"):
            if patch_yaml_icon(svc_dir / fname, new_url):
                yaml_patched += 1

        # patch index.json
        if patch_index_icon(index_data, slug, new_url):
            index_patched += 1

    # write updated index.json
    index_path.write_text(
        json.dumps(index_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )

    print(f"\nDone: {downloaded} icons downloaded, {skipped} skipped")
    print(f"  YAML files patched: {yaml_patched}")
    print(f"  Spec JSONs patched: {spec_patched}")
    print(f"  index.json entries patched: {index_patched}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

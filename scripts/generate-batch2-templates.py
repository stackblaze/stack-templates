#!/usr/bin/env python3
"""Generate Kubero templates for batch 2 catalog additions."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "services"
BASE = "https://raw.githubusercontent.com/stackblaze/stack-templates/main/services"

_spec = importlib.util.spec_from_file_location(
    "gen_top10", Path(__file__).parent / "generate-top10-templates.py"
)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

pg_addon = gen.pg_addon
mariadb_addon = gen.mariadb_addon
valkey_addon = gen.valkey_addon
template_doc = gen.template_doc
dump_yaml = gen.dump_yaml
write_pair = gen.write_pair

ICON_URLS = {
    "jellyfin": "https://avatars.githubusercontent.com/u/45698031?s=200&v=4",
    "formbricks": "https://avatars.githubusercontent.com/u/105877416?s=200&v=4",
    "openproject": "https://avatars.githubusercontent.com/u/1756674?s=200&v=4",
    "matomo": "https://avatars.githubusercontent.com/u/698038?s=200&v=4",
    "mealie": "https://avatars.githubusercontent.com/u/92342333?s=200&v=4",
    "nodebb": "https://avatars.githubusercontent.com/u/4449608?s=200&v=4",
    "syncthing": "https://avatars.githubusercontent.com/u/7628018?s=200&v=4",
    "hedgedoc": "https://avatars.githubusercontent.com/u/67865462?s=200&v=4",
    "freshrss": "https://avatars.githubusercontent.com/u/9414285?s=200&v=4",
    "vikunja": "https://avatars.githubusercontent.com/u/41270016?s=200&v=4",
}

CATALOG_ENTRIES = [
    {
        "name": "jellyfin",
        "description": "Free software media system that puts you in control of managing and streaming your movies, TV, and music.",
        "source": "https://github.com/jellyfin/jellyfin",
        "icon": ICON_URLS["jellyfin"],
        "website": "https://jellyfin.org/",
        "installation": "Mount media under /media or add libraries pointing to your storage after first login.",
        "categories": ["media", "utilities"],
        "screenshots": ["https://jellyfin.org/images/screenshots/home.png"],
        "links": ["https://jellyfin.org/docs/"],
        "addons": [],
        "stars": 35000,
        "language": "C#",
        "license": "GNU General Public License v2.0",
        "spdx_id": "GPL-2.0",
    },
    {
        "name": "formbricks",
        "description": "Open-source Qualtrics alternative for in-product micro-surveys and experience management.",
        "source": "https://github.com/formbricks/formbricks",
        "icon": ICON_URLS["formbricks"],
        "website": "https://formbricks.com/",
        "installation": (
            "Generate NEXTAUTH_SECRET, ENCRYPTION_KEY, CRON_SECRET, HUB_API_KEY, and CUBEJS_API_SECRET "
            "with openssl rand -hex 32 before production use."
        ),
        "categories": ["automation", "utilities", "work"],
        "screenshots": ["https://formbricks.com/images/og-image.png"],
        "links": ["https://formbricks.com/docs/self-hosting/setup/docker"],
        "addons": ["Cluster", "Valkey"],
        "stars": 12000,
        "language": "TypeScript",
        "license": "Other",
        "spdx_id": "NOASSERTION",
    },
    {
        "name": "openproject",
        "description": "Web-based project management system for location-independent team collaboration.",
        "source": "https://github.com/opf/openproject",
        "icon": ICON_URLS["openproject"],
        "website": "https://www.openproject.org/",
        "installation": "Set OPENPROJECT_HOST__NAME to your public hostname before first boot.",
        "categories": ["productivity", "work", "collaboration"],
        "screenshots": ["https://www.openproject.org/assets/images/enterprise/home/hero-screenshot-2024.png"],
        "links": ["https://www.openproject.org/docs/"],
        "addons": ["Cluster"],
        "stars": 12000,
        "language": "Ruby",
        "license": "GNU General Public License v3.0",
        "spdx_id": "GPL-3.0",
    },
    {
        "name": "matomo",
        "description": "Full-featured PHP analytics platform — privacy-focused alternative to Google Analytics.",
        "source": "https://github.com/matomo-org/matomo",
        "icon": ICON_URLS["matomo"],
        "website": "https://matomo.org/",
        "installation": "Complete the web setup wizard using the MariaDB credentials from this template.",
        "categories": ["data", "utilities", "work"],
        "screenshots": ["https://matomo.org/wp-content/uploads/2020/10/matomo-dashboard.png"],
        "links": ["https://matomo.org/docs/"],
        "addons": ["MariaDB"],
        "stars": 20000,
        "language": "PHP",
        "license": "GNU General Public License v3.0",
        "spdx_id": "GPL-3.0",
    },
    {
        "name": "mealie",
        "description": "Self-hosted recipe manager and meal planner with a clean, modern interface.",
        "source": "https://github.com/mealie-recipes/mealie",
        "icon": ICON_URLS["mealie"],
        "website": "https://mealie.io/",
        "installation": "Set BASE_URL to your public URL. Default login is created on first visit.",
        "categories": ["utilities", "productivity"],
        "screenshots": ["https://docs.mealie.io/assets/img/home-screen.png"],
        "links": ["https://docs.mealie.io/"],
        "addons": ["Cluster"],
        "stars": 8000,
        "language": "Python",
        "license": "GNU Affero General Public License v3.0",
        "spdx_id": "AGPL-3.0",
    },
    {
        "name": "nodebb",
        "description": "Next-generation forum software — powerful, mobile-ready, and fully customizable.",
        "source": "https://github.com/NodeBB/NodeBB",
        "icon": ICON_URLS["nodebb"],
        "website": "https://nodebb.org/",
        "installation": (
            "First boot runs automated setup via NODEBB_* env vars. Change admin password after login. "
            "Remove SETUP env or set to empty after successful initialization."
        ),
        "categories": ["communication", "social", "work"],
        "screenshots": ["https://nodebb.org/assets/images/nodebb-screenshot.png"],
        "links": ["https://docs.nodebb.org/"],
        "addons": ["Cluster"],
        "stars": 14000,
        "language": "JavaScript",
        "license": "GNU General Public License v3.0",
        "spdx_id": "GPL-3.0",
    },
    {
        "name": "syncthing",
        "description": "Continuous file synchronization — decentralized alternative to proprietary sync services.",
        "source": "https://github.com/syncthing/syncthing",
        "icon": ICON_URLS["syncthing"],
        "website": "https://syncthing.net/",
        "installation": "Access the web UI to pair devices and configure sync folders.",
        "categories": ["storage", "utilities"],
        "screenshots": ["https://docs.syncthing.net/_images/gs1-gui.png"],
        "links": ["https://docs.syncthing.net/"],
        "addons": [],
        "stars": 70000,
        "language": "Go",
        "license": "Mozilla Public License 2.0",
        "spdx_id": "MPL-2.0",
    },
    {
        "name": "hedgedoc",
        "description": "Collaborative markdown editor for real-time notes, docs, and knowledge sharing.",
        "source": "https://github.com/hedgedoc/hedgedoc",
        "icon": ICON_URLS["hedgedoc"],
        "website": "https://hedgedoc.org/",
        "installation": "Set CMD_DOMAIN to your public hostname and CMD_SESSION_SECRET to a random string.",
        "categories": ["documentation", "collaboration", "work"],
        "screenshots": ["https://hedgedoc.org/img/screenshot.png"],
        "links": ["https://docs.hedgedoc.org/"],
        "addons": ["Cluster"],
        "stars": 7000,
        "language": "TypeScript",
        "license": "GNU Affero General Public License v3.0",
        "spdx_id": "AGPL-3.0",
    },
    {
        "name": "freshrss",
        "description": "Self-hosted RSS feed aggregator — lightweight and extensible.",
        "source": "https://github.com/FreshRSS/FreshRSS",
        "icon": ICON_URLS["freshrss"],
        "website": "https://freshrss.org/",
        "installation": (
            "Auto-install runs once on first boot via FRESHRSS_INSTALL. "
            "Change the default admin password after login."
        ),
        "categories": ["utilities", "productivity"],
        "screenshots": ["https://freshrss.github.io/FreshRSS/img/FreshRSS-logo.png"],
        "links": ["https://freshrss.github.io/FreshRSS/en/"],
        "addons": ["MariaDB"],
        "stars": 15000,
        "language": "PHP",
        "license": "GNU Affero General Public License v3.0",
        "spdx_id": "AGPL-3.0",
    },
    {
        "name": "vikunja",
        "description": "The open-source to-do app — organize tasks, projects, and teams on all platforms.",
        "source": "https://github.com/go-vikunja/vikunja",
        "icon": ICON_URLS["vikunja"],
        "website": "https://vikunja.io/",
        "installation": "Set VIKUNJA_SERVICE_PUBLICURL and rotate VIKUNJA_SERVICE_JWTSECRET before production use.",
        "categories": ["productivity", "work", "utilities"],
        "screenshots": ["https://vikunja.io/images/screenshot.png"],
        "links": ["https://vikunja.io/docs/"],
        "addons": ["Cluster"],
        "stars": 9000,
        "language": "Go",
        "license": "GNU Affero General Public License v3.0",
        "spdx_id": "AGPL-3.0",
    },
]


def build_specs() -> None:
    # --- Jellyfin ---
    def jellyfin_spec(_ha: bool) -> dict:
        return template_doc(
            "jellyfin",
            "Jellyfin",
            CATALOG_ENTRIES[0]["description"],
            ICON_URLS["jellyfin"],
            CATALOG_ENTRIES[0]["source"],
            CATALOG_ENTRIES[0]["website"],
            CATALOG_ENTRIES[0]["categories"],
            CATALOG_ENTRIES[0]["installation"],
            CATALOG_ENTRIES[0]["screenshots"],
            CATALOG_ENTRIES[0]["links"],
            {
                "deploymentstrategy": "docker",
                "addons": [],
                "envVars": [
                    {"name": "JELLYFIN_PublishedServerUrl", "value": "{{KUBERO_APP_URL}}"},
                ],
                "extraVolumes": [
                    {
                        "accessModes": ["ReadWriteOnce"],
                        "emptyDir": False,
                        "mountPath": "/config",
                        "name": "jellyfin-config",
                        "size": "2Gi",
                    },
                    {
                        "accessModes": ["ReadWriteOnce"],
                        "emptyDir": False,
                        "mountPath": "/media",
                        "name": "jellyfin-media",
                        "size": "10Gi",
                    },
                ],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "8096",
                    "pullPolicy": "Always",
                    "repository": "jellyfin/jellyfin",
                    "tag": "latest",
                },
            },
        )

    write_pair("jellyfin", jellyfin_spec(False), jellyfin_spec(True))

    # --- Formbricks ---
    def formbricks_spec(ha: bool) -> dict:
        return template_doc(
            "formbricks",
            "Formbricks",
            CATALOG_ENTRIES[1]["description"],
            ICON_URLS["formbricks"],
            CATALOG_ENTRIES[1]["source"],
            CATALOG_ENTRIES[1]["website"],
            CATALOG_ENTRIES[1]["categories"],
            CATALOG_ENTRIES[1]["installation"],
            CATALOG_ENTRIES[1]["screenshots"],
            CATALOG_ENTRIES[1]["links"],
            {
                "deploymentstrategy": "docker",
                "addons": [
                    pg_addon("formbricks", "formbricks", "formbricks", "formbricks", 3 if ha else 1),
                    valkey_addon("formbricks", ha),
                ],
                "envVars": [
                    {"name": "WEBAPP_URL", "value": "{{KUBERO_APP_URL}}"},
                    {"name": "NEXTAUTH_URL", "value": "{{KUBERO_APP_URL}}"},
                    {
                        "name": "DATABASE_URL",
                        "value": "postgresql://formbricks:formbricks@formbricks-postgresql-rw:5432/formbricks?schema=public",
                    },
                    {"name": "REDIS_URL", "value": "redis://rfr-formbricks-valkey-readwrite:6379"},
                    {"name": "NEXTAUTH_SECRET", "value": "replace-with-openssl-rand-hex-32"},
                    {"name": "ENCRYPTION_KEY", "value": "replace-with-openssl-rand-hex-32"},
                    {"name": "CRON_SECRET", "value": "replace-with-openssl-rand-hex-32"},
                    {"name": "HUB_API_KEY", "value": "replace-with-openssl-rand-hex-32"},
                    {"name": "CUBEJS_API_SECRET", "value": "replace-with-openssl-rand-hex-32"},
                ],
                "extraVolumes": [],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "3000",
                    "pullPolicy": "Always",
                    "repository": "ghcr.io/formbricks/formbricks",
                    "tag": "latest",
                },
            },
        )

    write_pair("formbricks", formbricks_spec(False), formbricks_spec(True))

    # --- OpenProject ---
    def openproject_spec(ha: bool) -> dict:
        return template_doc(
            "openproject",
            "OpenProject",
            CATALOG_ENTRIES[2]["description"],
            ICON_URLS["openproject"],
            CATALOG_ENTRIES[2]["source"],
            CATALOG_ENTRIES[2]["website"],
            CATALOG_ENTRIES[2]["categories"],
            CATALOG_ENTRIES[2]["installation"],
            CATALOG_ENTRIES[2]["screenshots"],
            CATALOG_ENTRIES[2]["links"],
            {
                "deploymentstrategy": "docker",
                "addons": [
                    pg_addon("openproject", "openproject", "openproject", "openproject", 3 if ha else 1),
                ],
                "envVars": [
                    {"name": "OPENPROJECT_HTTPS", "value": "true"},
                    {"name": "OPENPROJECT_HOST__NAME", "value": "openproject.localhost"},
                    {
                        "name": "DATABASE_URL",
                        "value": "postgresql://openproject:openproject@openproject-postgresql-rw:5432/openproject",
                    },
                    {"name": "OPENPROJECT_SECRET_KEY_BASE", "value": "replace-with-openssl-rand-hex-64"},
                ],
                "extraVolumes": [
                    {
                        "accessModes": ["ReadWriteOnce"],
                        "emptyDir": False,
                        "mountPath": "/var/openproject/assets",
                        "name": "openproject-assets",
                        "size": "5Gi",
                    }
                ],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "8080",
                    "pullPolicy": "Always",
                    "repository": "openproject/openproject",
                    "tag": "16-slim",
                },
            },
        )

    write_pair("openproject", openproject_spec(False), openproject_spec(True))

    # --- Matomo ---
    def matomo_spec(ha: bool) -> dict:
        return template_doc(
            "matomo",
            "Matomo",
            CATALOG_ENTRIES[3]["description"],
            ICON_URLS["matomo"],
            CATALOG_ENTRIES[3]["source"],
            CATALOG_ENTRIES[3]["website"],
            CATALOG_ENTRIES[3]["categories"],
            CATALOG_ENTRIES[3]["installation"],
            CATALOG_ENTRIES[3]["screenshots"],
            CATALOG_ENTRIES[3]["links"],
            {
                "deploymentstrategy": "docker",
                "addons": [
                    mariadb_addon("matomo", "matomo", "matomo", "matomo", 3 if ha else 1, ha),
                ],
                "envVars": [
                    {"name": "MATOMO_DATABASE_ADAPTER", "value": "mysql"},
                    {"name": "MATOMO_DATABASE_HOST", "value": "matomo-mysql"},
                    {"name": "MATOMO_DATABASE_USERNAME", "value": "matomo"},
                    {"name": "MATOMO_DATABASE_PASSWORD", "value": "matomo"},
                    {"name": "MATOMO_DATABASE_DBNAME", "value": "matomo"},
                    {"name": "MATOMO_DATABASE_TABLES_PREFIX", "value": "matomo_"},
                ],
                "extraVolumes": [
                    {
                        "accessModes": ["ReadWriteOnce"],
                        "emptyDir": False,
                        "mountPath": "/var/www/html",
                        "name": "matomo-data",
                        "size": "2Gi",
                    }
                ],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "80",
                    "pullPolicy": "Always",
                    "repository": "matomo",
                    "tag": "latest",
                },
            },
        )

    write_pair("matomo", matomo_spec(False), matomo_spec(True))

    # --- Mealie ---
    def mealie_spec(ha: bool) -> dict:
        return template_doc(
            "mealie",
            "Mealie",
            CATALOG_ENTRIES[4]["description"],
            ICON_URLS["mealie"],
            CATALOG_ENTRIES[4]["source"],
            CATALOG_ENTRIES[4]["website"],
            CATALOG_ENTRIES[4]["categories"],
            CATALOG_ENTRIES[4]["installation"],
            CATALOG_ENTRIES[4]["screenshots"],
            CATALOG_ENTRIES[4]["links"],
            {
                "deploymentstrategy": "docker",
                "addons": [
                    pg_addon("mealie", "mealie", "mealie", "mealie", 3 if ha else 1),
                ],
                "envVars": [
                    {"name": "BASE_URL", "value": "{{KUBERO_APP_URL}}"},
                    {"name": "DB_ENGINE", "value": "postgres"},
                    {"name": "POSTGRES_SERVER", "value": "mealie-postgresql-rw"},
                    {"name": "POSTGRES_PORT", "value": "5432"},
                    {"name": "POSTGRES_USER", "value": "mealie"},
                    {"name": "POSTGRES_PASSWORD", "value": "mealie"},
                    {"name": "POSTGRES_DB", "value": "mealie"},
                    {"name": "TZ", "value": "Etc/UTC"},
                ],
                "extraVolumes": [
                    {
                        "accessModes": ["ReadWriteOnce"],
                        "emptyDir": False,
                        "mountPath": "/app/data",
                        "name": "mealie-data",
                        "size": "2Gi",
                    }
                ],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "9000",
                    "pullPolicy": "Always",
                    "repository": "ghcr.io/mealie-recipes/mealie",
                    "tag": "latest",
                },
            },
        )

    write_pair("mealie", mealie_spec(False), mealie_spec(True))

    # --- NodeBB ---
    def nodebb_spec(ha: bool) -> dict:
        return template_doc(
            "nodebb",
            "NodeBB",
            CATALOG_ENTRIES[5]["description"],
            ICON_URLS["nodebb"],
            CATALOG_ENTRIES[5]["source"],
            CATALOG_ENTRIES[5]["website"],
            CATALOG_ENTRIES[5]["categories"],
            CATALOG_ENTRIES[5]["installation"],
            CATALOG_ENTRIES[5]["screenshots"],
            CATALOG_ENTRIES[5]["links"],
            {
                "deploymentstrategy": "docker",
                "addons": [
                    pg_addon("nodebb", "nodebb", "nodebb", "nodebb", 3 if ha else 1),
                ],
                "envVars": [
                    {"name": "SETUP", "value": "true"},
                    {"name": "NODEBB_URL", "value": "{{KUBERO_APP_URL}}"},
                    {"name": "NODEBB_PORT", "value": "4567"},
                    {"name": "NODEBB_ADMIN_USERNAME", "value": "admin"},
                    {"name": "NODEBB_ADMIN_PASSWORD", "value": "change-me-on-first-login"},
                    {"name": "NODEBB_ADMIN_EMAIL", "value": "admin@example.com"},
                    {"name": "NODEBB_DB", "value": "postgres"},
                    {"name": "NODEBB_DB_HOST", "value": "nodebb-postgresql-rw"},
                    {"name": "NODEBB_DB_PORT", "value": "5432"},
                    {"name": "NODEBB_DB_USER", "value": "nodebb"},
                    {"name": "NODEBB_DB_PASSWORD", "value": "nodebb"},
                    {"name": "NODEBB_DB_NAME", "value": "nodebb"},
                ],
                "extraVolumes": [
                    {
                        "accessModes": ["ReadWriteOnce"],
                        "emptyDir": False,
                        "mountPath": "/usr/src/app/public/uploads",
                        "name": "nodebb-uploads",
                        "size": "2Gi",
                    },
                    {
                        "accessModes": ["ReadWriteOnce"],
                        "emptyDir": False,
                        "mountPath": "/opt/config",
                        "name": "nodebb-config",
                        "size": "1Gi",
                    },
                ],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "4567",
                    "pullPolicy": "Always",
                    "repository": "ghcr.io/nodebb/nodebb",
                    "tag": "latest",
                },
            },
        )

    write_pair("nodebb", nodebb_spec(False), nodebb_spec(True))

    # --- Syncthing ---
    def syncthing_spec(_ha: bool) -> dict:
        return template_doc(
            "syncthing",
            "Syncthing",
            CATALOG_ENTRIES[6]["description"],
            ICON_URLS["syncthing"],
            CATALOG_ENTRIES[6]["source"],
            CATALOG_ENTRIES[6]["website"],
            CATALOG_ENTRIES[6]["categories"],
            CATALOG_ENTRIES[6]["installation"],
            CATALOG_ENTRIES[6]["screenshots"],
            CATALOG_ENTRIES[6]["links"],
            {
                "deploymentstrategy": "docker",
                "addons": [],
                "envVars": [
                    {"name": "PUID", "value": "1000"},
                    {"name": "PGID", "value": "1000"},
                ],
                "extraVolumes": [
                    {
                        "accessModes": ["ReadWriteOnce"],
                        "emptyDir": False,
                        "mountPath": "/var/syncthing",
                        "name": "syncthing-config",
                        "size": "2Gi",
                    }
                ],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "8384",
                    "pullPolicy": "Always",
                    "repository": "syncthing/syncthing",
                    "tag": "latest",
                },
            },
        )

    write_pair("syncthing", syncthing_spec(False), syncthing_spec(True))

    # --- HedgeDoc ---
    def hedgedoc_spec(ha: bool) -> dict:
        return template_doc(
            "hedgedoc",
            "HedgeDoc",
            CATALOG_ENTRIES[7]["description"],
            ICON_URLS["hedgedoc"],
            CATALOG_ENTRIES[7]["source"],
            CATALOG_ENTRIES[7]["website"],
            CATALOG_ENTRIES[7]["categories"],
            CATALOG_ENTRIES[7]["installation"],
            CATALOG_ENTRIES[7]["screenshots"],
            CATALOG_ENTRIES[7]["links"],
            {
                "deploymentstrategy": "docker",
                "addons": [
                    pg_addon("hedgedoc", "hedgedoc", "hedgedoc", "hedgedoc", 3 if ha else 1),
                ],
                "envVars": [
                    {
                        "name": "CMD_DB_URL",
                        "value": "postgres://hedgedoc:hedgedoc@hedgedoc-postgresql-rw:5432/hedgedoc",
                    },
                    {"name": "CMD_DOMAIN", "value": "hedgedoc.localhost"},
                    {"name": "CMD_PROTOCOL_USESSL", "value": "true"},
                    {"name": "CMD_URL_ADDPORT", "value": "false"},
                    {"name": "CMD_SESSION_SECRET", "value": "replace-with-openssl-rand-hex-32"},
                ],
                "extraVolumes": [
                    {
                        "accessModes": ["ReadWriteOnce"],
                        "emptyDir": False,
                        "mountPath": "/hedgedoc/public/uploads",
                        "name": "hedgedoc-uploads",
                        "size": "2Gi",
                    }
                ],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "3000",
                    "pullPolicy": "Always",
                    "repository": "quay.io/hedgedoc/hedgedoc",
                    "tag": "1.10.8",
                },
            },
        )

    write_pair("hedgedoc", hedgedoc_spec(False), hedgedoc_spec(True))

    # --- FreshRSS ---
    freshrss_install = (
        "--default-user admin --default-password change-me --db-type mysql "
        "--db-host freshrss-mysql --db-user freshrss --db-password freshrss --db-base freshrss"
    )

    def freshrss_spec(ha: bool) -> dict:
        return template_doc(
            "freshrss",
            "FreshRSS",
            CATALOG_ENTRIES[8]["description"],
            ICON_URLS["freshrss"],
            CATALOG_ENTRIES[8]["source"],
            CATALOG_ENTRIES[8]["website"],
            CATALOG_ENTRIES[8]["categories"],
            CATALOG_ENTRIES[8]["installation"],
            CATALOG_ENTRIES[8]["screenshots"],
            CATALOG_ENTRIES[8]["links"],
            {
                "deploymentstrategy": "docker",
                "addons": [
                    mariadb_addon("freshrss", "freshrss", "freshrss", "freshrss", 3 if ha else 1, ha),
                ],
                "envVars": [
                    {"name": "TZ", "value": "Etc/UTC"},
                    {"name": "CRON_MIN", "value": "13,43"},
                    {"name": "FRESHRSS_INSTALL", "value": freshrss_install},
                ],
                "extraVolumes": [
                    {
                        "accessModes": ["ReadWriteOnce"],
                        "emptyDir": False,
                        "mountPath": "/var/www/FreshRSS/data",
                        "name": "freshrss-data",
                        "size": "1Gi",
                    }
                ],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "80",
                    "pullPolicy": "Always",
                    "repository": "freshrss/freshrss",
                    "tag": "latest",
                },
            },
        )

    write_pair("freshrss", freshrss_spec(False), freshrss_spec(True))

    # --- Vikunja ---
    def vikunja_spec(ha: bool) -> dict:
        return template_doc(
            "vikunja",
            "Vikunja",
            CATALOG_ENTRIES[9]["description"],
            ICON_URLS["vikunja"],
            CATALOG_ENTRIES[9]["source"],
            CATALOG_ENTRIES[9]["website"],
            CATALOG_ENTRIES[9]["categories"],
            CATALOG_ENTRIES[9]["installation"],
            CATALOG_ENTRIES[9]["screenshots"],
            CATALOG_ENTRIES[9]["links"],
            {
                "deploymentstrategy": "docker",
                "addons": [
                    pg_addon("vikunja", "vikunja", "vikunja", "vikunja", 3 if ha else 1),
                ],
                "envVars": [
                    {"name": "VIKUNJA_SERVICE_PUBLICURL", "value": "{{KUBERO_APP_URL}}"},
                    {"name": "VIKUNJA_SERVICE_JWTSECRET", "value": "replace-with-openssl-rand-hex-32"},
                    {"name": "VIKUNJA_SERVICE_ENABLEREGISTRATION", "value": "true"},
                    {"name": "VIKUNJA_DATABASE_TYPE", "value": "postgres"},
                    {"name": "VIKUNJA_DATABASE_HOST", "value": "vikunja-postgresql-rw"},
                    {"name": "VIKUNJA_DATABASE_USER", "value": "vikunja"},
                    {"name": "VIKUNJA_DATABASE_PASSWORD", "value": "vikunja"},
                    {"name": "VIKUNJA_DATABASE_DATABASE", "value": "vikunja"},
                ],
                "extraVolumes": [
                    {
                        "accessModes": ["ReadWriteOnce"],
                        "emptyDir": False,
                        "mountPath": "/app/vikunja/files",
                        "name": "vikunja-files",
                        "size": "2Gi",
                    }
                ],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "3456",
                    "pullPolicy": "Always",
                    "repository": "vikunja/vikunja",
                    "tag": "latest",
                },
            },
        )

    write_pair("vikunja", vikunja_spec(False), vikunja_spec(True))


def update_index() -> None:
    index_path = ROOT / "index.json"
    data = json.loads(index_path.read_text(encoding="utf-8"))
    existing = {s["name"] for s in data["services"]}

    for entry in CATALOG_ENTRIES:
        if entry["name"] in existing:
            # Refresh metadata for orphans already partially present
            for svc in data["services"]:
                if svc["name"] == entry["name"]:
                    svc["description"] = entry["description"]
                    svc["icon"] = entry["icon"]
                    svc["installation"] = entry["installation"]
                    svc["addons"] = entry["addons"]
                    svc["categories"] = entry["categories"]
                    svc["screenshots"] = entry["screenshots"]
                    svc["links"] = entry["links"]
                    svc["deploymentTypes"] = [
                        {
                            "id": "standard",
                            "label": "Standard",
                            "default": True,
                            "template": f"{BASE}/{entry['name']}/app.yaml",
                        },
                        {
                            "id": "ha",
                            "label": "High availability",
                            "template": f"{BASE}/{entry['name']}/app.ha.yaml",
                        },
                    ]
            continue

        service = {
            "name": entry["name"],
            "description": entry["description"],
            "source": entry["source"],
            "icon": entry["icon"],
            "website": entry["website"],
            "installation": entry["installation"],
            "architecture": entry.get("architecture", []),
            "categories": entry["categories"],
            "screenshots": entry["screenshots"],
            "links": entry["links"],
            "addons": entry["addons"],
            "stars": entry["stars"],
            "forks": max(entry["stars"] // 10, 1),
            "watchers": entry["stars"],
            "issues": 0,
            "last_updated": "2026-06-11T00:00:00Z",
            "last_pushed": "2026-06-11T00:00:00Z",
            "created_at": "2020-01-01T00:00:00Z",
            "size": 0,
            "language": entry.get("language", "TypeScript"),
            "gitops": False,
            "template": f"{BASE}/{entry['name']}/app.yaml",
            "status": "active",
            "license": entry["license"],
            "spdx_id": entry["spdx_id"],
            "dirname": entry["name"],
            "deploymentTypes": [
                {
                    "id": "standard",
                    "label": "Standard",
                    "default": True,
                    "template": f"{BASE}/{entry['name']}/app.yaml",
                },
                {
                    "id": "ha",
                    "label": "High availability",
                    "template": f"{BASE}/{entry['name']}/app.ha.yaml",
                },
            ],
        }
        data["services"].append(service)

    data["stats"]["total"] = len(data["services"])
    for entry in CATALOG_ENTRIES:
        for cat in entry["categories"]:
            data["categories"][cat] = data["categories"].get(cat, 0) + 1

    index_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build_specs()
    update_index()
    print("Generated batch 2 templates (10 apps).")

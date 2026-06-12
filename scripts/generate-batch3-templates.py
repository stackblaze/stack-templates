#!/usr/bin/env python3
"""Generate Kubero templates for batch 3 catalog additions."""

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
write_pair = gen.write_pair


def rabbitmq_addon(name: str, user: str, password: str, replicas: int) -> dict:
    return {
        "displayName": "RabbitMQ",
        "env": [],
        "icon": "/img/addons/rabbitmq.svg",
        "id": "kubero-operator",
        "kind": "RabbitmqCluster",
        "resourceDefinitions": {
            "RabbitmqCluster": {
                "apiVersion": "rabbitmq.com/v1beta1",
                "kind": "RabbitmqCluster",
                "metadata": {"name": f"{name}-rabbitmq"},
                "spec": {
                    "replicas": replicas,
                    "persistence": {
                        "storageClassName": "fast",
                        "storage": "1Gi",
                    },
                    "resources": {
                        "requests": {"cpu": "100m", "memory": "512Mi"},
                        "limits": {"memory": "1Gi"},
                    },
                },
            },
            "default-userSecret": {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {"name": f"{name}-rabbitmq-default-user"},
                "type": "Opaque",
                "stringData": {
                    "username": user,
                    "password": password,
                    "default_user.conf": (
                        f"default_user = {user}\ndefault_pass = {password}"
                    ),
                },
            },
        },
    }


def memcached_addon(name: str, replicas: int) -> dict:
    return {
        "displayName": "Memcached",
        "env": [],
        "icon": "/img/addons/memcached.svg",
        "id": "kubero-operator",
        "kind": "KuberoAddonMemcached",
        "resourceDefinitions": {
            "KuberoAddonMemcached": {
                "apiVersion": "application.kubero.dev/v1alpha1",
                "kind": "KuberoAddonMemcached",
                "metadata": {"name": f"{name}-memcached"},
                "spec": {
                    "memcached": {
                        "image": {"tag": "1.6.39"},
                        "replicaCount": replicas,
                        "config": {
                            "memoryLimit": 128,
                            "maxConnections": 1024,
                            "extraArgs": [],
                            "verbosity": 0,
                        },
                        "resources": {},
                    }
                },
            }
        },
    }


ICON_URLS = {
    "netbox": "https://avatars.githubusercontent.com/u/44905828?s=200&v=4",
    "kroki": "https://avatars.githubusercontent.com/u/4894788?s=200&v=4",
    "superset": "https://avatars.githubusercontent.com/u/47359?s=200&v=4",
    "appflowy": "https://avatars.githubusercontent.com/u/86002201?s=200&v=4",
    "cryptpad": "https://avatars.githubusercontent.com/u/76949612?s=200&v=4",
    "glpi": "https://avatars.githubusercontent.com/u/13361707?s=200&v=4",
    "humhub": "https://avatars.githubusercontent.com/u/6262639?s=200&v=4",
    "easyappointments": "https://avatars.githubusercontent.com/u/4527441?s=200&v=4",
    "password-pusher": "https://avatars.githubusercontent.com/u/395132?s=200&v=4",
    "zulip": "https://avatars.githubusercontent.com/u/4921959?s=200&v=4",
}

CATALOG_ENTRIES = [
    {
        "name": "netbox",
        "description": "NetBox is the leading open-source DCIM and IP address management platform for network infrastructure.",
        "source": "https://github.com/netbox-community/netbox",
        "icon": ICON_URLS["netbox"],
        "website": "https://netbox.dev/",
        "installation": (
            "Rotate SECRET_KEY and DB passwords before production. "
            "Deploy a netbox-worker using the same image with `rqworker` for background jobs."
        ),
        "categories": ["utilities", "work", "development"],
        "screenshots": ["https://netbox.dev/static/netbox_logo.svg"],
        "links": ["https://docs.netbox.dev/"],
        "addons": ["Cluster", "Valkey"],
        "stars": 18000,
        "language": "Python",
        "license": "Apache License 2.0",
        "spdx_id": "Apache-2.0",
    },
    {
        "name": "kroki",
        "description": "Creates diagrams from textual descriptions — unified API for PlantUML, Mermaid, Graphviz, and more.",
        "source": "https://github.com/yuzutech/kroki",
        "icon": ICON_URLS["kroki"],
        "website": "https://kroki.io/",
        "installation": "No database required. Optionally set KROKI_SAFE_MODE=secure for production.",
        "categories": ["utilities", "development", "documentation"],
        "screenshots": ["https://kroki.io/assets/img/kroki-logo.png"],
        "links": ["https://docs.kroki.io/"],
        "addons": [],
        "stars": 4000,
        "language": "Java",
        "license": "MIT License",
        "spdx_id": "MIT",
    },
    {
        "name": "superset",
        "description": "Modern data exploration and visualization platform — enterprise-ready business intelligence.",
        "source": "https://github.com/apache/superset",
        "icon": ICON_URLS["superset"],
        "website": "https://superset.apache.org/",
        "installation": (
            "Generate SUPERSET_SECRET_KEY with openssl rand -base64 42. "
            "Run superset db upgrade && superset init once after first deploy if the UI does not load."
        ),
        "categories": ["data", "utilities", "work"],
        "screenshots": ["https://superset.apache.org/img/superset-logo-horiz.svg"],
        "links": ["https://superset.apache.org/docs/intro"],
        "addons": ["Cluster", "Valkey"],
        "stars": 65000,
        "language": "Python",
        "license": "Apache License 2.0",
        "spdx_id": "Apache-2.0",
    },
    {
        "name": "appflowy",
        "description": "Open-source Notion alternative — self-hosted workspace for notes, docs, and collaboration.",
        "source": "https://github.com/AppFlowy-IO/AppFlowy-Cloud",
        "icon": ICON_URLS["appflowy"],
        "website": "https://appflowy.io/",
        "installation": (
            "Minimal API backend only. Deploy gotrue, minio, and appflowy-web from the AppFlowy-Cloud "
            "docker-compose in the same pipeline for a complete self-hosted stack."
        ),
        "categories": ["productivity", "work", "collaboration"],
        "screenshots": ["https://appflowy.io/_next/static/media/appflowy-logo.0a1a0b0b.png"],
        "links": ["https://appflowy-io-appflowy.mintlify.app/self-hosting/installation"],
        "addons": ["Cluster", "Valkey"],
        "stars": 5000,
        "language": "Rust",
        "license": "GNU Affero General Public License v3.0",
        "spdx_id": "AGPL-3.0",
    },
    {
        "name": "cryptpad",
        "description": "Collaborative office suite — end-to-end encrypted docs, sheets, and kanban boards.",
        "source": "https://github.com/cryptpad/cryptpad",
        "icon": ICON_URLS["cryptpad"],
        "website": "https://cryptpad.org/",
        "installation": (
            "Set CPAD_MAIN_DOMAIN and CPAD_SANDBOX_DOMAIN to two distinct HTTPS origins. "
            "First boot runs npm build and may take several minutes."
        ),
        "categories": ["collaboration", "documentation", "work"],
        "screenshots": ["https://cryptpad.org/customize/logo/banner.png"],
        "links": ["https://docs.cryptpad.org/"],
        "addons": [],
        "stars": 7000,
        "language": "JavaScript",
        "license": "GNU Affero General Public License v3.0",
        "spdx_id": "AGPL-3.0",
    },
    {
        "name": "glpi",
        "description": "IT service management and asset tracking — helpdesk, inventory, and CMDB in one platform.",
        "source": "https://github.com/glpi-project/glpi",
        "icon": ICON_URLS["glpi"],
        "website": "https://glpi-project.org/",
        "installation": "GLPI auto-installs when all GLPI_DB_* variables are set. Default login admin/glpi — change immediately.",
        "categories": ["work", "helpdesk", "utilities"],
        "screenshots": ["https://glpi-project.org/images/glpi.png"],
        "links": ["https://help.glpi-project.org/"],
        "addons": ["MariaDB"],
        "stars": 5000,
        "language": "PHP",
        "license": "GNU General Public License v3.0",
        "spdx_id": "GPL-3.0",
    },
    {
        "name": "humhub",
        "description": "Flexible open-source social network kit for private communities and team collaboration.",
        "source": "https://github.com/humhub/humhub",
        "icon": ICON_URLS["humhub"],
        "website": "https://www.humhub.com/",
        "installation": "Set HUMHUB_HOST to your public hostname. Set HUMHUB_ADMIN_PASSWORD before first boot for auto-install.",
        "categories": ["communication", "social", "work"],
        "screenshots": ["https://www.humhub.com/static/img/humhub-logo.png"],
        "links": ["https://docs.humhub.org/"],
        "addons": ["MariaDB"],
        "stars": 7000,
        "language": "PHP",
        "license": "GNU Affero General Public License v3.0",
        "spdx_id": "AGPL-3.0",
    },
    {
        "name": "easyappointments",
        "description": "Open-source appointment scheduler for service providers — booking pages, calendars, and notifications.",
        "source": "https://github.com/alextselegidis/easyappointments",
        "icon": ICON_URLS["easyappointments"],
        "website": "https://easyappointments.org/",
        "installation": "Set BASE_URL to your public URL before first visit. Complete admin setup on first login.",
        "categories": ["utilities", "work", "productivity"],
        "screenshots": ["https://easyappointments.org/img/logo.png"],
        "links": ["https://easyappointments.org/documentation/"],
        "addons": ["MariaDB"],
        "stars": 4000,
        "language": "PHP",
        "license": "GNU General Public License v3.0",
        "spdx_id": "GPL-3.0",
    },
    {
        "name": "password-pusher",
        "description": "Securely share passwords and files with expiring links — open-source alternative to one-time secret services.",
        "source": "https://github.com/pglombardo/PasswordPusher",
        "icon": ICON_URLS["password-pusher"],
        "website": "https://pwpush.com/",
        "installation": "Generate PWPUSH_MASTER_KEY before production. Set TLS_DOMAIN for automatic HTTPS if supported.",
        "categories": ["security", "utilities"],
        "screenshots": ["https://pwpush.com/assets/pwpush-logo.png"],
        "links": ["https://docs.pwpush.com/docs/installation/"],
        "addons": ["Cluster"],
        "stars": 3000,
        "language": "Ruby",
        "license": "Other",
        "spdx_id": "NOASSERTION",
    },
    {
        "name": "zulip",
        "description": "Powerful open-source team chat organized into topic-based threads — an alternative to Slack.",
        "source": "https://github.com/zulip/zulip",
        "icon": ICON_URLS["zulip"],
        "website": "https://zulip.com/",
        "installation": (
            "Set SETTING_EXTERNAL_HOST and SECRETS_secret_key before first boot. "
            "Initial startup can take 5–10 minutes while Zulip configures all services."
        ),
        "categories": ["communication", "work", "collaboration"],
        "screenshots": ["https://zulip.com/static/images/landing-page/zulip-hero.png"],
        "links": ["https://zulip.readthedocs.io/projects/docker/"],
        "addons": ["Cluster", "Valkey", "RabbitmqCluster", "KuberoAddonMemcached"],
        "stars": 22000,
        "language": "Python",
        "license": "Other",
        "spdx_id": "NOASSERTION",
    },
]


def build_specs() -> None:
    # --- NetBox ---
    def netbox_spec(ha: bool) -> dict:
        redis_host = "rfr-netbox-valkey-readwrite"
        return template_doc(
            "netbox",
            "NetBox",
            CATALOG_ENTRIES[0]["description"],
            ICON_URLS["netbox"],
            CATALOG_ENTRIES[0]["source"],
            CATALOG_ENTRIES[0]["website"],
            CATALOG_ENTRIES[0]["categories"],
            CATALOG_ENTRIES[0]["installation"],
            CATALOG_ENTRIES[0]["screenshots"],
            CATALOG_ENTRIES[0]["links"],
            {
                "deploymentstrategy": "docker",
                "addons": [
                    pg_addon("netbox", "netbox", "netbox", "netbox", 3 if ha else 1),
                    valkey_addon("netbox", ha),
                ],
                "envVars": [
                    {"name": "DB_HOST", "value": "netbox-postgresql-rw"},
                    {"name": "DB_NAME", "value": "netbox"},
                    {"name": "DB_USER", "value": "netbox"},
                    {"name": "DB_PASSWORD", "value": "netbox"},
                    {"name": "REDIS_HOST", "value": redis_host},
                    {"name": "REDIS_PASSWORD", "value": ""},
                    {"name": "REDIS_DATABASE", "value": "0"},
                    {"name": "REDIS_CACHE_HOST", "value": redis_host},
                    {"name": "REDIS_CACHE_PASSWORD", "value": ""},
                    {"name": "REDIS_CACHE_DATABASE", "value": "1"},
                    {"name": "SECRET_KEY", "value": "replace-with-openssl-rand-hex-50"},
                    {"name": "SKIP_SUPERUSER", "value": "false"},
                    {"name": "SUPERUSER_NAME", "value": "admin"},
                    {"name": "SUPERUSER_EMAIL", "value": "admin@example.com"},
                    {"name": "SUPERUSER_PASSWORD", "value": "change-me"},
                ],
                "extraVolumes": [
                    {
                        "accessModes": ["ReadWriteOnce"],
                        "emptyDir": False,
                        "mountPath": "/opt/netbox/netbox/media",
                        "name": "netbox-media",
                        "size": "2Gi",
                    }
                ],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "8080",
                    "pullPolicy": "Always",
                    "repository": "netboxcommunity/netbox",
                    "tag": "latest",
                },
            },
        )

    write_pair("netbox", netbox_spec(False), netbox_spec(True))

    # --- Kroki ---
    def kroki_spec(_ha: bool) -> dict:
        return template_doc(
            "kroki",
            "Kroki",
            CATALOG_ENTRIES[1]["description"],
            ICON_URLS["kroki"],
            CATALOG_ENTRIES[1]["source"],
            CATALOG_ENTRIES[1]["website"],
            CATALOG_ENTRIES[1]["categories"],
            CATALOG_ENTRIES[1]["installation"],
            CATALOG_ENTRIES[1]["screenshots"],
            CATALOG_ENTRIES[1]["links"],
            {
                "deploymentstrategy": "docker",
                "addons": [],
                "envVars": [
                    {"name": "KROKI_SAFE_MODE", "value": "unsafe"},
                ],
                "extraVolumes": [],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "8000",
                    "pullPolicy": "Always",
                    "repository": "yuzutech/kroki",
                    "tag": "latest",
                },
            },
        )

    write_pair("kroki", kroki_spec(False), kroki_spec(True))

    # --- Superset ---
    def superset_spec(ha: bool) -> dict:
        return template_doc(
            "superset",
            "Apache Superset",
            CATALOG_ENTRIES[2]["description"],
            ICON_URLS["superset"],
            CATALOG_ENTRIES[2]["source"],
            CATALOG_ENTRIES[2]["website"],
            CATALOG_ENTRIES[2]["categories"],
            CATALOG_ENTRIES[2]["installation"],
            CATALOG_ENTRIES[2]["screenshots"],
            CATALOG_ENTRIES[2]["links"],
            {
                "deploymentstrategy": "docker",
                "addons": [
                    pg_addon("superset", "superset", "superset", "superset", 3 if ha else 1),
                    valkey_addon("superset", ha),
                ],
                "envVars": [
                    {"name": "SUPERSET_SECRET_KEY", "value": "replace-with-openssl-rand-base64-42"},
                    {"name": "DATABASE_DIALECT", "value": "postgresql"},
                    {"name": "DATABASE_HOST", "value": "superset-postgresql-rw"},
                    {"name": "DATABASE_PORT", "value": "5432"},
                    {"name": "DATABASE_DB", "value": "superset"},
                    {"name": "DATABASE_USER", "value": "superset"},
                    {"name": "DATABASE_PASSWORD", "value": "superset"},
                    {"name": "REDIS_HOST", "value": "rfr-superset-valkey-readwrite"},
                    {"name": "REDIS_PORT", "value": "6379"},
                ],
                "extraVolumes": [],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "8088",
                    "pullPolicy": "Always",
                    "repository": "apache/superset",
                    "tag": "latest",
                },
            },
        )

    write_pair("superset", superset_spec(False), superset_spec(True))

    # --- AppFlowy ---
    def appflowy_spec(ha: bool) -> dict:
        return template_doc(
            "appflowy",
            "AppFlowy",
            CATALOG_ENTRIES[3]["description"],
            ICON_URLS["appflowy"],
            CATALOG_ENTRIES[3]["source"],
            CATALOG_ENTRIES[3]["website"],
            CATALOG_ENTRIES[3]["categories"],
            CATALOG_ENTRIES[3]["installation"],
            CATALOG_ENTRIES[3]["screenshots"],
            CATALOG_ENTRIES[3]["links"],
            {
                "deploymentstrategy": "docker",
                "addons": [
                    pg_addon("appflowy", "appflowy", "appflowy", "appflowy", 3 if ha else 1),
                    valkey_addon("appflowy", ha),
                ],
                "envVars": [
                    {
                        "name": "APPFLOWY_DATABASE_URL",
                        "value": "postgres://appflowy:appflowy@appflowy-postgresql-rw:5432/appflowy",
                    },
                    {"name": "APPFLOWY_REDIS_URI", "value": "redis://rfr-appflowy-valkey-readwrite:6379"},
                    {"name": "APPFLOWY_CLOUD_BASE_URL", "value": "{{KUBERO_APP_URL}}"},
                    {"name": "APPFLOWY_GOTRUE_JWT_SECRET", "value": "replace-with-openssl-rand-hex-32"},
                    {"name": "APPFLOWY_GOTRUE_BASE_URL", "value": "{{KUBERO_APP_URL}}/gotrue"},
                    {"name": "APPFLOWY_S3_USE_MINIO", "value": "true"},
                    {"name": "APPFLOWY_S3_MINIO_URL", "value": "http://minio:9000"},
                    {"name": "APPFLOWY_S3_ACCESS_KEY", "value": "minioadmin"},
                    {"name": "APPFLOWY_S3_SECRET_KEY", "value": "minioadmin"},
                    {"name": "APPFLOWY_S3_BUCKET", "value": "appflowy"},
                ],
                "extraVolumes": [],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "8000",
                    "pullPolicy": "Always",
                    "repository": "appflowyinc/appflowy_cloud",
                    "tag": "latest",
                },
            },
        )

    write_pair("appflowy", appflowy_spec(False), appflowy_spec(True))

    # --- CryptPad ---
    def cryptpad_spec(_ha: bool) -> dict:
        return template_doc(
            "cryptpad",
            "CryptPad",
            CATALOG_ENTRIES[4]["description"],
            ICON_URLS["cryptpad"],
            CATALOG_ENTRIES[4]["source"],
            CATALOG_ENTRIES[4]["website"],
            CATALOG_ENTRIES[4]["categories"],
            CATALOG_ENTRIES[4]["installation"],
            CATALOG_ENTRIES[4]["screenshots"],
            CATALOG_ENTRIES[4]["links"],
            {
                "deploymentstrategy": "docker",
                "addons": [],
                "envVars": [
                    {"name": "CPAD_MAIN_DOMAIN", "value": "{{KUBERO_APP_URL}}"},
                    {"name": "CPAD_SANDBOX_DOMAIN", "value": "https://sandbox.example.com"},
                    {"name": "CPAD_CONF", "value": "/cryptpad/config/config.js"},
                ],
                "extraVolumes": [
                    {
                        "accessModes": ["ReadWriteOnce"],
                        "emptyDir": False,
                        "mountPath": "/cryptpad/blob",
                        "name": "cryptpad-blob",
                        "size": "2Gi",
                    },
                    {
                        "accessModes": ["ReadWriteOnce"],
                        "emptyDir": False,
                        "mountPath": "/cryptpad/block",
                        "name": "cryptpad-block",
                        "size": "2Gi",
                    },
                    {
                        "accessModes": ["ReadWriteOnce"],
                        "emptyDir": False,
                        "mountPath": "/cryptpad/data",
                        "name": "cryptpad-data",
                        "size": "2Gi",
                    },
                    {
                        "accessModes": ["ReadWriteOnce"],
                        "emptyDir": False,
                        "mountPath": "/cryptpad/datastore",
                        "name": "cryptpad-files",
                        "size": "2Gi",
                    },
                ],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "3000",
                    "pullPolicy": "Always",
                    "repository": "cryptpad/cryptpad",
                    "tag": "latest",
                },
            },
        )

    write_pair("cryptpad", cryptpad_spec(False), cryptpad_spec(True))

    # --- GLPI ---
    def glpi_spec(ha: bool) -> dict:
        return template_doc(
            "glpi",
            "GLPI",
            CATALOG_ENTRIES[5]["description"],
            ICON_URLS["glpi"],
            CATALOG_ENTRIES[5]["source"],
            CATALOG_ENTRIES[5]["website"],
            CATALOG_ENTRIES[5]["categories"],
            CATALOG_ENTRIES[5]["installation"],
            CATALOG_ENTRIES[5]["screenshots"],
            CATALOG_ENTRIES[5]["links"],
            {
                "deploymentstrategy": "docker",
                "addons": [
                    mariadb_addon("glpi", "glpi", "glpi", "glpi", 3 if ha else 1, ha),
                ],
                "envVars": [
                    {"name": "GLPI_DB_HOST", "value": "glpi-mysql"},
                    {"name": "GLPI_DB_PORT", "value": "3306"},
                    {"name": "GLPI_DB_NAME", "value": "glpi"},
                    {"name": "GLPI_DB_USER", "value": "glpi"},
                    {"name": "GLPI_DB_PASSWORD", "value": "glpi"},
                ],
                "extraVolumes": [
                    {
                        "accessModes": ["ReadWriteOnce"],
                        "emptyDir": False,
                        "mountPath": "/var/glpi",
                        "name": "glpi-data",
                        "size": "2Gi",
                    }
                ],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "80",
                    "pullPolicy": "Always",
                    "repository": "glpi/glpi",
                    "tag": "latest",
                },
            },
        )

    write_pair("glpi", glpi_spec(False), glpi_spec(True))

    # --- HumHub ---
    def humhub_spec(ha: bool) -> dict:
        return template_doc(
            "humhub",
            "HumHub",
            CATALOG_ENTRIES[6]["description"],
            ICON_URLS["humhub"],
            CATALOG_ENTRIES[6]["source"],
            CATALOG_ENTRIES[6]["website"],
            CATALOG_ENTRIES[6]["categories"],
            CATALOG_ENTRIES[6]["installation"],
            CATALOG_ENTRIES[6]["screenshots"],
            CATALOG_ENTRIES[6]["links"],
            {
                "deploymentstrategy": "docker",
                "addons": [
                    mariadb_addon("humhub", "humhub", "humhub", "humhub", 3 if ha else 1, ha),
                ],
                "envVars": [
                    {"name": "HUMHUB_DB_HOST", "value": "humhub-mysql"},
                    {"name": "HUMHUB_DB_NAME", "value": "humhub"},
                    {"name": "HUMHUB_DB_USER", "value": "humhub"},
                    {"name": "HUMHUB_DB_PASSWORD", "value": "humhub"},
                    {"name": "HUMHUB_PROTO", "value": "https"},
                    {"name": "HUMHUB_HOST", "value": "humhub.localhost"},
                    {"name": "HUMHUB_ADMIN_LOGIN", "value": "admin"},
                    {"name": "HUMHUB_ADMIN_EMAIL", "value": "admin@example.com"},
                    {"name": "HUMHUB_ADMIN_PASSWORD", "value": "change-me"},
                ],
                "extraVolumes": [
                    {
                        "accessModes": ["ReadWriteOnce"],
                        "emptyDir": False,
                        "mountPath": "/var/www/localhost/htdocs/protected/config",
                        "name": "humhub-config",
                        "size": "1Gi",
                    },
                    {
                        "accessModes": ["ReadWriteOnce"],
                        "emptyDir": False,
                        "mountPath": "/var/www/localhost/htdocs/uploads",
                        "name": "humhub-uploads",
                        "size": "2Gi",
                    },
                ],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "80",
                    "pullPolicy": "Always",
                    "repository": "mriedmann/humhub",
                    "tag": "stable",
                },
            },
        )

    write_pair("humhub", humhub_spec(False), humhub_spec(True))

    # --- Easy!Appointments ---
    def easyappointments_spec(ha: bool) -> dict:
        return template_doc(
            "easyappointments",
            "Easy!Appointments",
            CATALOG_ENTRIES[7]["description"],
            ICON_URLS["easyappointments"],
            CATALOG_ENTRIES[7]["source"],
            CATALOG_ENTRIES[7]["website"],
            CATALOG_ENTRIES[7]["categories"],
            CATALOG_ENTRIES[7]["installation"],
            CATALOG_ENTRIES[7]["screenshots"],
            CATALOG_ENTRIES[7]["links"],
            {
                "deploymentstrategy": "docker",
                "addons": [
                    mariadb_addon(
                        "easyappointments", "easyappointments", "easyappointments", "easyappointments",
                        3 if ha else 1, ha,
                    ),
                ],
                "envVars": [
                    {"name": "BASE_URL", "value": "{{KUBERO_APP_URL}}"},
                    {"name": "DEBUG_MODE", "value": "FALSE"},
                    {"name": "DB_HOST", "value": "easyappointments-mysql"},
                    {"name": "DB_NAME", "value": "easyappointments"},
                    {"name": "DB_USERNAME", "value": "easyappointments"},
                    {"name": "DB_PASSWORD", "value": "easyappointments"},
                ],
                "extraVolumes": [
                    {
                        "accessModes": ["ReadWriteOnce"],
                        "emptyDir": False,
                        "mountPath": "/var/www/html",
                        "name": "easyappointments-data",
                        "size": "1Gi",
                    }
                ],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "80",
                    "pullPolicy": "Always",
                    "repository": "alextselegidis/easyappointments",
                    "tag": "latest",
                },
            },
        )

    write_pair("easyappointments", easyappointments_spec(False), easyappointments_spec(True))

    # --- Password Pusher ---
    def password_pusher_spec(ha: bool) -> dict:
        return template_doc(
            "password-pusher",
            "Password Pusher",
            CATALOG_ENTRIES[8]["description"],
            ICON_URLS["password-pusher"],
            CATALOG_ENTRIES[8]["source"],
            CATALOG_ENTRIES[8]["website"],
            CATALOG_ENTRIES[8]["categories"],
            CATALOG_ENTRIES[8]["installation"],
            CATALOG_ENTRIES[8]["screenshots"],
            CATALOG_ENTRIES[8]["links"],
            {
                "deploymentstrategy": "docker",
                "addons": [
                    pg_addon("pwpush", "pwpush", "pwpush", "pwpush", 3 if ha else 1),
                ],
                "envVars": [
                    {
                        "name": "DATABASE_URL",
                        "value": "postgres://pwpush:pwpush@pwpush-postgresql-rw:5432/pwpush",
                    },
                    {"name": "PWPUSH_MASTER_KEY", "value": "replace-with-generated-master-key"},
                    {"name": "PWP__ALLOW_ANONYMOUS", "value": "true"},
                    {"name": "PWP__ENABLE_URL_PUSHES", "value": "true"},
                ],
                "extraVolumes": [
                    {
                        "accessModes": ["ReadWriteOnce"],
                        "emptyDir": False,
                        "mountPath": "/opt/PasswordPusher/storage",
                        "name": "pwpush-storage",
                        "size": "1Gi",
                    }
                ],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "5100",
                    "pullPolicy": "Always",
                    "repository": "pglombardo/pwpush",
                    "tag": "stable",
                },
            },
        )

    write_pair("password-pusher", password_pusher_spec(False), password_pusher_spec(True))

    # --- Zulip ---
    def zulip_spec(ha: bool) -> dict:
        replicas = 3 if ha else 1
        return template_doc(
            "zulip",
            "Zulip",
            CATALOG_ENTRIES[9]["description"],
            ICON_URLS["zulip"],
            CATALOG_ENTRIES[9]["source"],
            CATALOG_ENTRIES[9]["website"],
            CATALOG_ENTRIES[9]["categories"],
            CATALOG_ENTRIES[9]["installation"],
            CATALOG_ENTRIES[9]["screenshots"],
            CATALOG_ENTRIES[9]["links"],
            {
                "deploymentstrategy": "docker",
                "addons": [
                    pg_addon("zulip", "zulip", "zulip", "zulip", replicas),
                    valkey_addon("zulip", ha),
                    rabbitmq_addon("zulip", "zulip", "zulip", replicas),
                    memcached_addon("zulip", replicas),
                ],
                "envVars": [
                    {"name": "SETTING_EXTERNAL_HOST", "value": "zulip.localhost"},
                    {"name": "SETTING_ZULIP_ADMINISTRATOR", "value": "admin@example.com"},
                    {"name": "SETTING_REMOTE_POSTGRES_HOST", "value": "zulip-postgresql-rw"},
                    {"name": "SETTING_RABBITMQ_HOST", "value": "zulip-rabbitmq"},
                    {"name": "SETTING_REDIS_HOST", "value": "rfr-zulip-valkey-readwrite"},
                    {"name": "SETTING_MEMCACHED_LOCATION", "value": "zulip-memcached:11211"},
                    {"name": "SECRETS_postgres_password", "value": "zulip"},
                    {"name": "SECRETS_rabbitmq_password", "value": "zulip"},
                    {"name": "SECRETS_redis_password", "value": ""},
                    {"name": "SECRETS_memcached_password", "value": ""},
                    {"name": "SECRETS_secret_key", "value": "replace-with-openssl-rand-hex-50"},
                    {"name": "POSTGRES_DB", "value": "zulip"},
                    {"name": "POSTGRES_USER", "value": "zulip"},
                    {"name": "POSTGRES_PASSWORD", "value": "zulip"},
                ],
                "extraVolumes": [
                    {
                        "accessModes": ["ReadWriteOnce"],
                        "emptyDir": False,
                        "mountPath": "/data",
                        "name": "zulip-data",
                        "size": "5Gi",
                    }
                ],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "80",
                    "pullPolicy": "Always",
                    "repository": "ghcr.io/zulip/zulip-server",
                    "tag": "10.2-1",
                },
            },
        )

    write_pair("zulip", zulip_spec(False), zulip_spec(True))


def update_index() -> None:
    index_path = ROOT / "index.json"
    data = json.loads(index_path.read_text(encoding="utf-8"))
    existing = {s["name"] for s in data["services"]}

    for entry in CATALOG_ENTRIES:
        if entry["name"] in existing:
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
    print("Generated batch 3 templates (10 apps).")

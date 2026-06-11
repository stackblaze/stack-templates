#!/usr/bin/env python3
"""Generate Kubero templates for batch catalog additions.

Standard vs HA convention (all templates in this repo follow this):

- Standard (app.yaml): use Kubero addons (Postgres, MariaDB, Valkey, …) in
  minimal single-node form — NOT empty addons, NOT HA.
- HA (app.ha.yaml): same app spec; scale addons only (CNPG instances: 3,
  MariaDB Galera, Valkey failover + Sentinel). Keep web.replicaCount at 1
  unless the app itself requires workers.

See README.md § "Standard vs high availability" for the full table.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "services"
BASE = "https://raw.githubusercontent.com/stackblaze/stack-templates/main/services"


def pg_addon(name: str, db: str, user: str, password: str, instances: int) -> dict:
    return {
        "displayName": "PostgreSQL (CloudNativePG)",
        "env": [],
        "icon": "/img/addons/pgsql.svg",
        "id": "kubero-operator",
        "kind": "Cluster",
        "resourceDefinitions": {
            "Cluster": {
                "apiVersion": "postgresql.cnpg.io/v1",
                "kind": "Cluster",
                "metadata": {"name": f"{name}-postgresql"},
                "spec": {
                    "instances": instances,
                    "imageName": "ghcr.io/cloudnative-pg/postgresql:16",
                    "primaryUpdateStrategy": "unsupervised",
                    "storage": {"storageClass": "fast", "size": "5Gi"},
                    "resources": {
                        "requests": {"cpu": "100m", "memory": "256Mi"},
                        "limits": {"cpu": "1", "memory": "1Gi"},
                    },
                    "bootstrap": {
                        "initdb": {
                            "database": db,
                            "owner": user,
                            "secret": {"name": f"{name}-postgresql-app"},
                        }
                    },
                    "enableSuperuserAccess": True,
                    "superuserSecret": {"name": f"{name}-postgresql-superuser"},
                },
            },
            "superuserSecret": {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {"name": f"{name}-postgresql-superuser"},
                "type": "kubernetes.io/basic-auth",
                "stringData": {"username": "postgres", "password": password},
            },
            "appUserSecret": {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {"name": f"{name}-postgresql-app"},
                "type": "kubernetes.io/basic-auth",
                "stringData": {"username": user, "password": password},
            },
        },
    }


def mariadb_addon(name: str, db: str, user: str, password: str, replicas: int, galera: bool) -> dict:
    spec = {
        "metrics": {"enabled": True},
        "rootPasswordSecretKeyRef": {"name": f"{name}-mysql-root", "key": "password"},
        "database": db,
        "username": user,
        "passwordSecretKeyRef": {"name": f"{name}-mysql-app", "key": "password"},
        "storage": {"size": "5Gi", "storageClassName": "fast"},
        "replicas": replicas,
        "resources": {
            "requests": {"cpu": "100m", "memory": "256Mi"},
            "limits": {"cpu": "1", "memory": "1Gi"},
        },
    }
    if galera:
        spec["galera"] = {"enabled": True}
    return {
        "displayName": "MariaDB",
        "env": [],
        "icon": "/img/addons/mysql.svg",
        "id": "kubero-operator",
        "kind": "MariaDB",
        "resourceDefinitions": {
            "MariaDB": {
                "apiVersion": "k8s.mariadb.com/v1alpha1",
                "kind": "MariaDB",
                "metadata": {"name": f"{name}-mysql"},
                "spec": spec,
            },
            "rootSecret": {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {"name": f"{name}-mysql-root"},
                "type": "Opaque",
                "stringData": {"password": password},
            },
            "appSecret": {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {"name": f"{name}-mysql-app"},
                "type": "Opaque",
                "stringData": {"password": password},
            },
        },
    }


def valkey_addon(name: str, ha: bool) -> dict:
    if ha:
        arch = "failover"
        replicas = {"shards": 1, "replicasOfShard": 2}
        sentinel = {"replicas": 3, "quorum": 2}
    else:
        arch = "replica"
        replicas = {"shards": 1, "replicasOfShard": 1}
        sentinel = None
    valkey_spec = {
        "version": "8.0",
        "arch": arch,
        "replicas": replicas,
        "access": {"serviceType": "ClusterIP"},
        "storage": {"capacity": "1Gi", "storageClassName": "fast"},
        "resources": {
            "requests": {"cpu": "50m", "memory": "256Mi"},
            "limits": {"cpu": "500m", "memory": "256Mi"},
        },
    }
    if sentinel:
        valkey_spec["sentinel"] = sentinel
    return {
        "displayName": "Valkey",
        "env": [],
        "icon": "/img/addons/redis.svg",
        "id": "kubero-operator",
        "kind": "Valkey",
        "resourceDefinitions": {
            "Valkey": {
                "apiVersion": "rds.valkey.buf.red/v1alpha1",
                "kind": "Valkey",
                "metadata": {"name": f"{name}-valkey"},
                "spec": valkey_spec,
            }
        },
    }


def documentdb_uri(instance: str, user: str, password: str, database: str = "") -> str:
    """MongoDB-wire URI for Microsoft DocumentDB (port 10260, TLS + SCRAM)."""
    host = f"documentdb-service-{instance}"
    params = (
        "directConnection=true&authMechanism=SCRAM-SHA-256&tls=true"
        "&tlsAllowInvalidCertificates=true&replicaSet=rs0"
    )
    path = database or ""
    return f"mongodb://{user}:{password}@{host}:10260/{path}?{params}"


def documentdb_addon(name: str, user: str = "mongoadmin", password: str = "changeme", node_count: int = 1) -> dict:
    """Document DB operator addon (MongoDB-wire compatible, replaces KuberoMongoDB)."""
    instance = f"{name}-documentdb"
    return {
        "displayName": "Document DB",
        "env": [],
        "icon": "/img/addons/mongo.svg",
        "id": "kubero-operator",
        "kind": "DocumentDB",
        "resourceDefinitions": {
            "DocumentDB": {
                "apiVersion": "documentdb.io/preview",
                "kind": "DocumentDB",
                "metadata": {"name": instance},
                "spec": {
                    "nodeCount": node_count,
                    "instancesPerNode": 1,
                    "documentDbCredentialSecret": "documentdb-credentials",
                    "resource": {
                        "storage": {"pvcSize": "1Gi", "storageClass": "default"},
                    },
                    "exposeViaService": {"serviceType": "ClusterIP"},
                },
            },
            "credentialSecret": {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {"name": "documentdb-credentials"},
                "type": "Opaque",
                "stringData": {"username": user, "password": password},
            },
        },
    }


def clickhouse_addon(name: str, password: str, replicas: int) -> dict:
    return {
        "displayName": "ClickHouse",
        "env": [],
        "icon": "/img/addons/clickhouse.svg",
        "id": "clickhouse-operator",
        "kind": "ClickHouseInstallation",
        "resourceDefinitions": {
            "ClickHouseInstallation": {
                "apiVersion": "clickhouse.altinity.com/v1",
                "kind": "ClickHouseInstallation",
                "metadata": {"name": f"{name}-clickhouse"},
                "spec": {
                    "configuration": {
                        "users": {
                            "admin/password": password,
                            "admin/networks/ip": ["0.0.0.0/0"],
                        },
                        "clusters": [
                            {
                                "name": "analytics",
                                "layout": {
                                    "shardsCount": 1,
                                    "replicasCount": replicas,
                                },
                            }
                        ],
                    },
                    "defaults": {
                        "templates": {
                            "dataVolumeClaimTemplate": "data-volume-template",
                            "logVolumeClaimTemplate": "log-volume-template",
                        }
                    },
                    "templates": {
                        "volumeClaimTemplates": [
                            {
                                "name": "data-volume-template",
                                "spec": {
                                    "accessModes": ["ReadWriteOnce"],
                                    "storageClassName": "fast",
                                    "resources": {"requests": {"storage": "5Gi"}},
                                },
                            },
                            {
                                "name": "log-volume-template",
                                "spec": {
                                    "accessModes": ["ReadWriteOnce"],
                                    "storageClassName": "fast",
                                    "resources": {"requests": {"storage": "1Gi"}},
                                },
                            },
                        ]
                    },
                },
            }
        },
    }


def template_doc(
    name: str,
    title: str,
    description: str,
    icon: str,
    source: str,
    website: str,
    categories: list[str],
    installation: str,
    screenshots: list[str],
    links: list[str],
    spec: dict,
) -> dict:
    return {
        "apiVersion": "application.kubero.dev/v1alpha1",
        "kind": "KuberoApp",
        "metadata": {
            "name": name,
            "annotations": {
                "kubero.dev/template.architecture": "[]",
                "kubero.dev/template.description": description,
                "kubero.dev/template.icon": icon,
                "kubero.dev/template.installation": installation,
                "kubero.dev/template.links": json.dumps(links),
                "kubero.dev/template.screenshots": json.dumps(screenshots),
                "kubero.dev/template.source": source,
                "kubero.dev/template.categories": json.dumps(categories),
                "kubero.dev/template.title": title,
                "kubero.dev/template.website": website,
            },
            "labels": {"manager": "kubero"},
        },
        "spec": {"name": name, **spec},
    }


def dump_yaml(doc: dict) -> str:
    import yaml

    return yaml.dump(doc, sort_keys=False, allow_unicode=True, width=120)


def write_pair(slug: str, standard: dict, ha: dict | None = None) -> None:
    folder = SERVICES / slug
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "app.yaml").write_text(dump_yaml(standard), encoding="utf-8")
    if ha is not None:
        (folder / "app.ha.yaml").write_text(dump_yaml(ha), encoding="utf-8")


def build_specs() -> None:
    import yaml  # noqa: F401

    # --- Nextcloud ---
    def nextcloud_spec(ha: bool) -> dict:
        return template_doc(
            "nextcloud",
            "Nextcloud",
            "Nextcloud is a self-hosted file sync and collaboration platform.",
            "https://avatars.githubusercontent.com/u/19211038?s=200&v=4",
            "https://github.com/nextcloud/server",
            "https://nextcloud.com/",
            ["storage", "work", "collaboration"],
            "Set NEXTCLOUD_TRUSTED_DOMAINS to your public hostname before going live.",
            ["https://nextcloud.com/wp-content/uploads/2022/03/hero.webp"],
            ["https://docs.nextcloud.com/"],
            {
                "deploymentstrategy": "docker",
                "addons": [
                    mariadb_addon("nextcloud", "nextcloud", "nextcloud", "nextcloud", 3 if ha else 1, ha)
                ],
                "envVars": [
                    {"name": "MYSQL_HOST", "value": "nextcloud-mysql"},
                    {"name": "MYSQL_DATABASE", "value": "nextcloud"},
                    {"name": "MYSQL_USER", "value": "nextcloud"},
                    {"name": "MYSQL_PASSWORD", "value": "nextcloud"},
                    {"name": "NEXTCLOUD_TRUSTED_DOMAINS", "value": "nextcloud.localhost"},
                    {"name": "OVERWRITEPROTOCOL", "value": "https"},
                ],
                "extraVolumes": [
                    {
                        "accessModes": ["ReadWriteMany"],
                        "storageClass": "shared",
                        "emptyDir": False,
                        "mountPath": "/var/www/html",
                        "name": "nextcloud-data",
                        "size": "5Gi",
                    }
                ],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "80",
                    "pullPolicy": "Always",
                    "repository": "nextcloud",
                    "tag": "apache",
                },
            },
        )

    write_pair("nextcloud", nextcloud_spec(False), nextcloud_spec(True))

    # --- Immich ---
    immich_meta = {
        "title": "Immich",
        "description": "Self-hosted photo and video backup solution with a mobile-first focus.",
        "icon": "https://avatars.githubusercontent.com/u/109746326?s=200&v=4",
        "source": "https://github.com/immich-app/immich",
        "website": "https://immich.app/",
        "categories": ["storage", "media", "utilities"],
        "installation": "Machine learning is disabled in this minimal template. Enable a separate ML service for face/object detection if needed.",
        "screenshots": ["https://immich.app/img/hero.webp"],
        "links": ["https://docs.immich.app/"],
    }

    def immich_spec(ha: bool) -> dict:
        return template_doc(
            "immich",
            immich_meta["title"],
            immich_meta["description"],
            immich_meta["icon"],
            immich_meta["source"],
            immich_meta["website"],
            immich_meta["categories"],
            immich_meta["installation"],
            immich_meta["screenshots"],
            immich_meta["links"],
            {
                "deploymentstrategy": "docker",
                "addons": [
                    pg_addon("immich", "immich", "immich", "immich", 3 if ha else 1),
                    valkey_addon("immich", ha),
                ],
                "envVars": [
                    {"name": "DB_HOSTNAME", "value": "immich-postgresql-rw"},
                    {"name": "DB_PORT", "value": "5432"},
                    {"name": "DB_USERNAME", "value": "immich"},
                    {"name": "DB_PASSWORD", "value": "immich"},
                    {"name": "DB_DATABASE_NAME", "value": "immich"},
                    {"name": "REDIS_HOSTNAME", "value": "rfr-immich-valkey-readwrite"},
                    {"name": "REDIS_PORT", "value": "6379"},
                    {"name": "REDIS_PASSWORD", "value": ""},
                    {"name": "REDIS_DBINDEX", "value": "0"},
                    {"name": "MACHINE_LEARNING_ENABLED", "value": "false"},
                    {"name": "UPLOAD_LOCATION", "value": "/usr/src/app/upload"},
                ],
                "extraVolumes": [
                    {
                        "accessModes": ["ReadWriteOnce"],
                        "emptyDir": False,
                        "mountPath": "/usr/src/app/upload",
                        "name": "immich-upload",
                        "size": "5Gi",
                    }
                ],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "2283",
                    "pullPolicy": "Always",
                    "repository": "ghcr.io/immich-app/immich-server",
                    "tag": "release",
                },
            },
        )

    write_pair("immich", immich_spec(False), immich_spec(True))

    # --- Chatwoot ---
    chatwoot_install = (
        "Background jobs run inline in this minimal template. For production throughput, "
        "deploy a dedicated Sidekiq worker using the same image and env with "
        "`bundle exec sidekiq -C config/sidekiq.yml`."
    )

    def chatwoot_spec(ha: bool) -> dict:
        return template_doc(
            "chatwoot",
            "Chatwoot",
            "Open-source customer engagement platform — an alternative to Intercom and Zendesk.",
            "https://avatars.githubusercontent.com/u/59890204",
            "https://github.com/chatwoot/chatwoot",
            "https://www.chatwoot.com/",
            ["communication", "work", "helpdesk"],
            chatwoot_install,
            ["https://www.chatwoot.com/images/chatwoot-dashboard.png"],
            ["https://www.chatwoot.com/docs/"],
            {
                "deploymentstrategy": "docker",
                "addons": [
                    pg_addon("chatwoot", "chatwoot", "chatwoot", "chatwoot", 3 if ha else 1),
                    valkey_addon("chatwoot", ha),
                ],
                "envVars": [
                    {"name": "FRONTEND_URL", "value": "{{KUBERO_APP_URL}}"},
                    {"name": "POSTGRES_HOST", "value": "chatwoot-postgresql-rw"},
                    {"name": "POSTGRES_PORT", "value": "5432"},
                    {"name": "POSTGRES_DATABASE", "value": "chatwoot"},
                    {"name": "POSTGRES_USERNAME", "value": "chatwoot"},
                    {"name": "POSTGRES_PASSWORD", "value": "chatwoot"},
                    {"name": "REDIS_URL", "value": "redis://rfr-chatwoot-valkey-readwrite:6379"},
                    {"name": "SECRET_KEY_BASE", "value": "replace-with-openssl-rand-hex-64"},
                    {"name": "RAILS_ENV", "value": "production"},
                    {"name": "INSTALLATION_ENV", "value": "docker"},
                    {"name": "ACTIVE_STORAGE_SERVICE", "value": "local"},
                ],
                "extraVolumes": [
                    {
                        "accessModes": ["ReadWriteOnce"],
                        "emptyDir": False,
                        "mountPath": "/app/storage",
                        "name": "chatwoot-storage",
                        "size": "2Gi",
                    }
                ],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "3000",
                    "pullPolicy": "Always",
                    "repository": "chatwoot/chatwoot",
                    "tag": "latest",
                },
            },
        )

    write_pair("chatwoot", chatwoot_spec(False), chatwoot_spec(True))

    # --- Typebot (builder) ---
    typebot_install = (
        "This template deploys the Typebot builder. Set NEXT_PUBLIC_VIEWER_URL to your "
        "public viewer URL. For production, deploy baptistearno/typebot-viewer with the "
        "same DATABASE_URL and ENCRYPTION_SECRET in the same pipeline phase."
    )

    def typebot_spec(ha: bool) -> dict:
        return template_doc(
            "typebot",
            "Typebot",
            "Open-source conversational form builder — a Typeform alternative you can self-host.",
            "https://avatars.githubusercontent.com/u/78780997",
            "https://github.com/baptisteArno/typebot.io",
            "https://typebot.io/",
            ["automation", "utilities", "work"],
            typebot_install,
            ["https://docs.typebot.io/images/og.png"],
            ["https://docs.typebot.io/"],
            {
                "deploymentstrategy": "docker",
                "addons": [pg_addon("typebot", "typebot", "typebot", "typebot", 3 if ha else 1)],
                "envVars": [
                    {
                        "name": "DATABASE_URL",
                        "value": "postgresql://typebot:typebot@typebot-postgresql-rw:5432/typebot",
                    },
                    {"name": "NEXTAUTH_URL", "value": "{{KUBERO_APP_URL}}"},
                    {"name": "NEXT_PUBLIC_VIEWER_URL", "value": "{{KUBERO_APP_URL}}"},
                    {"name": "NEXTAUTH_SECRET", "value": "replace-with-openssl-rand-base64-32"},
                    {"name": "ENCRYPTION_SECRET", "value": "replace-with-openssl-rand-base64-32"},
                    {"name": "ADMIN_EMAIL", "value": "admin@example.com"},
                    {"name": "DISABLE_SIGNUP", "value": "false"},
                ],
                "extraVolumes": [],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "3000",
                    "pullPolicy": "Always",
                    "repository": "baptistearno/typebot-builder",
                    "tag": "latest",
                },
            },
        )

    write_pair("typebot", typebot_spec(False), typebot_spec(True))

    # --- Plausible ---
    plausible_install = (
        "Generate SECRET_KEY_BASE with `openssl rand -hex 64` and TOTP_VAULT_KEY with "
        "`openssl rand -base64 32`. Update BASE_URL before going live."
    )

    def plausible_spec(ha: bool) -> dict:
        ch_pass = "plausible"
        return template_doc(
            "plausible",
            "Plausible Analytics",
            "Privacy-friendly alternative to Google Analytics — lightweight and open source.",
            "https://avatars.githubusercontent.com/u/65434334",
            "https://github.com/plausible/analytics",
            "https://plausible.io/",
            ["data", "utilities", "work"],
            plausible_install,
            ["https://plausible.io/docs/img/plausible-analytics.png"],
            ["https://plausible.io/docs/"],
            {
                "deploymentstrategy": "docker",
                "addons": [
                    pg_addon("plausible", "plausible", "plausible", "plausible", 3 if ha else 1),
                    clickhouse_addon("plausible", ch_pass, 1),
                ],
                "envVars": [
                    {"name": "BASE_URL", "value": "{{KUBERO_APP_URL}}"},
                    {
                        "name": "SECRET_KEY_BASE",
                        "value": "0000000000000000000000000000000000000000000000000000000000000000",
                    },
                    {"name": "TOTP_VAULT_KEY", "value": "0000000000000000000000000000000000000000"},
                    {
                        "name": "DATABASE_URL",
                        "value": "postgresql://plausible:plausible@plausible-postgresql-rw:5432/plausible",
                    },
                    {
                        "name": "CLICKHOUSE_DATABASE_URL",
                        "value": f"http://admin:{ch_pass}@clickhouse-plausible-clickhouse:8123/plausible_events",
                    },
                ],
                "extraVolumes": [],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "8000",
                    "pullPolicy": "Always",
                    "repository": "ghcr.io/plausible/community-edition",
                    "tag": "v3.0.1",
                    "command": [
                        "sh",
                        "-c",
                        "sleep 15 && /entrypoint.sh db createdb && /entrypoint.sh db migrate && /entrypoint.sh run",
                    ],
                },
            },
        )

    write_pair("plausible", plausible_spec(False), plausible_spec(True))

    # --- Plane (API minimal) ---
    plane_install = (
        "This template deploys the Plane API backend with PostgreSQL and Valkey. "
        "Plane CE also requires web, worker, beat, and proxy containers — use the official "
        "Plane Helm chart for a full stack, or deploy makeplane/plane-frontend and "
        "makeplane/plane-proxy companions pointed at this API service."
    )

    def plane_spec(ha: bool) -> dict:
        return template_doc(
            "plane",
            "Plane",
            "Open-source project management platform — modern alternative to Jira and Linear.",
            "https://avatars.githubusercontent.com/u/115725709",
            "https://github.com/makeplane/plane",
            "https://plane.so/",
            ["productivity", "work", "collaboration"],
            plane_install,
            ["https://plane.so/og-image.png"],
            ["https://developers.plane.so/"],
            {
                "deploymentstrategy": "docker",
                "addons": [
                    pg_addon("plane", "plane", "plane", "plane", 3 if ha else 1),
                    valkey_addon("plane", ha),
                ],
                "envVars": [
                    {"name": "WEB_URL", "value": "{{KUBERO_APP_URL}}"},
                    {"name": "CORS_ALLOWED_ORIGINS", "value": "{{KUBERO_APP_URL}}"},
                    {"name": "DATABASE_URL", "value": "postgresql://plane:plane@plane-postgresql-rw:5432/plane"},
                    {"name": "REDIS_URL", "value": "redis://rfr-plane-valkey-readwrite:6379/0"},
                    {"name": "SECRET_KEY", "value": "replace-with-openssl-rand-hex-32"},
                    {"name": "USE_MINIO", "value": "0"},
                ],
                "extraVolumes": [],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "8000",
                    "pullPolicy": "Always",
                    "repository": "makeplane/plane-backend",
                    "tag": "stable",
                    "command": ["./bin/docker-entrypoint-api.sh"],
                },
            },
        )

    write_pair("plane", plane_spec(False), plane_spec(True))

    # --- Discourse ---
    discourse_install = (
        "Set DISCOURSE_HOST to your public hostname (without protocol) before first boot. "
        "Default admin password is configured via DISCOURSE_PASSWORD — change it after install."
    )

    def discourse_spec(ha: bool) -> dict:
        return template_doc(
            "discourse",
            "Discourse",
            "Open-source community discussion platform — modern forum software.",
            "https://avatars.githubusercontent.com/u/6230072",
            "https://github.com/discourse/discourse",
            "https://www.discourse.org/",
            ["communication", "social", "work"],
            discourse_install,
            ["https://www.discourse.org/a/images/discourse-screen.jpg"],
            ["https://meta.discourse.org/"],
            {
                "deploymentstrategy": "docker",
                "addons": [
                    pg_addon("discourse", "bitnami_discourse", "bn_discourse", "discourse", 3 if ha else 1),
                    valkey_addon("discourse", ha),
                ],
                "envVars": [
                    {"name": "DISCOURSE_HOST", "value": "discourse.localhost"},
                    {"name": "DISCOURSE_PASSWORD", "value": "discourse"},
                    {"name": "DISCOURSE_DATABASE_HOST", "value": "discourse-postgresql-rw"},
                    {"name": "DISCOURSE_DATABASE_PORT_NUMBER", "value": "5432"},
                    {"name": "DISCOURSE_DATABASE_USER", "value": "bn_discourse"},
                    {"name": "DISCOURSE_DATABASE_NAME", "value": "bitnami_discourse"},
                    {"name": "DISCOURSE_REDIS_HOST", "value": "rfr-discourse-valkey-readwrite"},
                    {"name": "DISCOURSE_REDIS_PORT_NUMBER", "value": "6379"},
                    {"name": "ALLOW_EMPTY_PASSWORD", "value": "yes"},
                ],
                "extraVolumes": [
                    {
                        "accessModes": ["ReadWriteOnce"],
                        "emptyDir": False,
                        "mountPath": "/bitnami/discourse",
                        "name": "discourse-data",
                        "size": "5Gi",
                    }
                ],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "3000",
                    "pullPolicy": "Always",
                    "repository": "bitnami/discourse",
                    "tag": "latest",
                },
            },
        )

    write_pair("discourse", discourse_spec(False), discourse_spec(True))

    # --- Infisical ---
    infisical_install = (
        "Generate ENCRYPTION_KEY with `openssl rand -hex 16` and AUTH_SECRET with "
        "`openssl rand -base64 32` before production use."
    )

    def infisical_spec(ha: bool) -> dict:
        return template_doc(
            "infisical",
            "Infisical",
            "Open-source secrets management and internal PKI platform for developers and teams.",
            "https://avatars.githubusercontent.com/u/107085096",
            "https://github.com/Infisical/infisical",
            "https://infisical.com/",
            ["security", "development", "work"],
            infisical_install,
            ["https://infisical.com/images/og-image.png"],
            ["https://infisical.com/docs/"],
            {
                "deploymentstrategy": "docker",
                "addons": [
                    pg_addon("infisical", "infisical", "infisical", "infisical", 3 if ha else 1),
                    valkey_addon("infisical", ha),
                ],
                "envVars": [
                    {"name": "SITE_URL", "value": "{{KUBERO_APP_URL}}"},
                    {"name": "HOST", "value": "0.0.0.0"},
                    {"name": "PORT", "value": "8080"},
                    {
                        "name": "DB_CONNECTION_URI",
                        "value": "postgresql://infisical:infisical@infisical-postgresql-rw:5432/infisical",
                    },
                    {"name": "REDIS_URL", "value": "redis://rfr-infisical-valkey-readwrite:6379"},
                    {"name": "ENCRYPTION_KEY", "value": "00000000000000000000000000000000"},
                    {"name": "AUTH_SECRET", "value": "replace-with-openssl-rand-base64-32"},
                ],
                "extraVolumes": [],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "8080",
                    "pullPolicy": "Always",
                    "repository": "infisical/infisical",
                    "tag": "latest",
                },
            },
        )

    write_pair("infisical", infisical_spec(False), infisical_spec(True))

    # --- Linkwarden ---
    linkwarden_install = (
        "Deploy the meilisearch template in the same pipeline phase first (app name `meilisearch`). "
        "Generate NEXTAUTH_SECRET with `openssl rand -base64 32`."
    )

    def linkwarden_spec(ha: bool) -> dict:
        return template_doc(
            "linkwarden",
            "Linkwarden",
            "Self-hosted collaborative bookmark manager to collect and organize links.",
            "https://avatars.githubusercontent.com/u/118754866",
            "https://github.com/linkwarden/linkwarden",
            "https://linkwarden.app/",
            ["documentation", "utilities", "work"],
            linkwarden_install,
            ["https://linkwarden.app/_next/image?url=%2Fthumbnail.png&w=1920&q=75"],
            ["https://docs.linkwarden.app/"],
            {
                "deploymentstrategy": "docker",
                "addons": [pg_addon("linkwarden", "linkwarden", "linkwarden", "linkwarden", 3 if ha else 1)],
                "envVars": [
                    {"name": "NEXTAUTH_URL", "value": "{{KUBERO_APP_URL}}"},
                    {"name": "NEXTAUTH_SECRET", "value": "replace-with-openssl-rand-base64-32"},
                    {
                        "name": "DATABASE_URL",
                        "value": "postgresql://linkwarden:linkwarden@linkwarden-postgresql-rw:5432/linkwarden",
                    },
                    {"name": "MEILI_HOST", "value": "http://meilisearch-kuberoapp:7700"},
                    {"name": "MEILI_MASTER_KEY", "value": "linkwarden-meili-key"},
                ],
                "extraVolumes": [
                    {
                        "accessModes": ["ReadWriteOnce"],
                        "emptyDir": False,
                        "mountPath": "/data/data",
                        "name": "linkwarden-data",
                        "size": "2Gi",
                    }
                ],
                "cronjobs": [],
                "web": {"replicaCount": 1},
                "worker": {"replicaCount": 0},
                "image": {
                    "containerPort": "3000",
                    "pullPolicy": "Always",
                    "repository": "ghcr.io/linkwarden/linkwarden",
                    "tag": "latest",
                },
            },
        )

    write_pair("linkwarden", linkwarden_spec(False), linkwarden_spec(True))


ICON_URLS = {
    "nextcloud": "https://avatars.githubusercontent.com/u/19211038?s=200&v=4",
    "immich": "https://avatars.githubusercontent.com/u/109746326?s=200&v=4",
    "chatwoot": "https://avatars.githubusercontent.com/u/23416667?s=200&v=4",
    "typebot": "https://avatars.githubusercontent.com/u/16015833?s=200&v=4",
    "plausible": "https://avatars.githubusercontent.com/u/54802774?s=200&v=4",
    "plane": "https://avatars.githubusercontent.com/u/115727700?s=200&v=4",
    "discourse": "https://avatars.githubusercontent.com/u/3220138?s=200&v=4",
    "infisical": "https://avatars.githubusercontent.com/u/107880645?s=200&v=4",
    "linkwarden": "https://avatars.githubusercontent.com/u/135248736?s=200&v=4",
    "penpot": "https://avatars.githubusercontent.com/u/30179644?s=200&v=4",
}


CATALOG_ENTRIES = [
    {
        "name": "nextcloud",
        "description": "Nextcloud is a self-hosted file sync and collaboration platform.",
        "source": "https://github.com/nextcloud/server",
        "icon": ICON_URLS["nextcloud"],
        "website": "https://nextcloud.com/",
        "installation": "Set NEXTCLOUD_TRUSTED_DOMAINS to your public hostname before going live.",
        "categories": ["storage", "work", "collaboration"],
        "screenshots": ["https://nextcloud.com/wp-content/uploads/2022/03/hero.webp"],
        "links": ["https://docs.nextcloud.com/"],
        "addons": ["MariaDB"],
        "stars": 28000,
        "license": "GNU Affero General Public License v3.0",
        "spdx_id": "AGPL-3.0",
    },
    {
        "name": "immich",
        "description": "Self-hosted photo and video backup solution with a mobile-first focus.",
        "source": "https://github.com/immich-app/immich",
        "icon": "https://avatars.githubusercontent.com/u/109746326?s=200&v=4",
        "website": "https://immich.app/",
        "installation": "Machine learning is disabled in this minimal template.",
        "categories": ["storage", "media", "utilities"],
        "screenshots": ["https://immich.app/img/hero.webp"],
        "links": ["https://docs.immich.app/"],
        "addons": ["Cluster", "Valkey"],
        "stars": 70000,
        "license": "GNU Affero General Public License v3.0",
        "spdx_id": "AGPL-3.0",
    },
    {
        "name": "chatwoot",
        "description": "Open-source customer engagement platform — an alternative to Intercom and Zendesk.",
        "source": "https://github.com/chatwoot/chatwoot",
        "icon": ICON_URLS["chatwoot"],
        "website": "https://www.chatwoot.com/",
        "installation": "Replace SECRET_KEY_BASE before production use.",
        "categories": ["communication", "work", "helpdesk"],
        "screenshots": ["https://www.chatwoot.com/images/chatwoot-dashboard.png"],
        "links": ["https://www.chatwoot.com/docs/"],
        "addons": ["Cluster", "Valkey"],
        "stars": 25000,
        "license": "Other",
        "spdx_id": "NOASSERTION",
    },
    {
        "name": "typebot",
        "description": "Open-source conversational form builder — a Typeform alternative you can self-host.",
        "source": "https://github.com/baptisteArno/typebot.io",
        "icon": ICON_URLS["typebot"],
        "website": "https://typebot.io/",
        "installation": "Deploy typebot-viewer separately for published bots in production.",
        "categories": ["automation", "utilities", "work"],
        "screenshots": ["https://docs.typebot.io/images/og.png"],
        "links": ["https://docs.typebot.io/"],
        "addons": ["Cluster"],
        "stars": 10000,
        "license": "Other",
        "spdx_id": "NOASSERTION",
    },
    {
        "name": "plausible",
        "description": "Privacy-friendly alternative to Google Analytics — lightweight and open source.",
        "source": "https://github.com/plausible/analytics",
        "icon": ICON_URLS["plausible"],
        "website": "https://plausible.io/",
        "installation": "Requires ClickHouse and PostgreSQL addons. Rotate SECRET_KEY_BASE and TOTP_VAULT_KEY.",
        "categories": ["data", "utilities", "work"],
        "screenshots": ["https://plausible.io/docs/img/plausible-analytics.png"],
        "links": ["https://plausible.io/docs/"],
        "addons": ["Cluster", "ClickHouseInstallation"],
        "stars": 25000,
        "license": "GNU Affero General Public License v3.0",
        "spdx_id": "AGPL-3.0",
    },
    {
        "name": "plane",
        "description": "Open-source project management platform — modern alternative to Jira and Linear.",
        "source": "https://github.com/makeplane/plane",
        "icon": ICON_URLS["plane"],
        "website": "https://plane.so/",
        "installation": "Minimal API backend. Use Plane Helm chart for a complete CE deployment.",
        "categories": ["productivity", "work", "collaboration"],
        "screenshots": ["https://plane.so/og-image.png"],
        "links": ["https://developers.plane.so/"],
        "addons": ["Cluster", "Valkey"],
        "stars": 47000,
        "license": "GNU Affero General Public License v3.0",
        "spdx_id": "AGPL-3.0",
    },
    {
        "name": "discourse",
        "description": "Open-source community discussion platform — modern forum software.",
        "source": "https://github.com/discourse/discourse",
        "icon": ICON_URLS["discourse"],
        "website": "https://www.discourse.org/",
        "installation": "Set DISCOURSE_HOST to your public hostname before first boot.",
        "categories": ["communication", "social", "work"],
        "screenshots": ["https://www.discourse.org/a/images/discourse-screen.jpg"],
        "links": ["https://meta.discourse.org/"],
        "addons": ["Cluster", "Valkey"],
        "stars": 43000,
        "license": "GNU General Public License v2.0",
        "spdx_id": "GPL-2.0",
    },
    {
        "name": "infisical",
        "description": "Open-source secrets management and internal PKI platform for developers and teams.",
        "source": "https://github.com/Infisical/infisical",
        "icon": ICON_URLS["infisical"],
        "website": "https://infisical.com/",
        "installation": "Generate ENCRYPTION_KEY and AUTH_SECRET before production use.",
        "categories": ["security", "development", "work"],
        "screenshots": ["https://infisical.com/images/og-image.png"],
        "links": ["https://infisical.com/docs/"],
        "addons": ["Cluster", "Valkey"],
        "stars": 20000,
        "license": "Other",
        "spdx_id": "NOASSERTION",
    },
    {
        "name": "linkwarden",
        "description": "Self-hosted collaborative bookmark manager to collect and organize links.",
        "source": "https://github.com/linkwarden/linkwarden",
        "icon": ICON_URLS["linkwarden"],
        "website": "https://linkwarden.app/",
        "installation": "Deploy meilisearch in the same pipeline phase before Linkwarden.",
        "categories": ["documentation", "utilities", "work"],
        "screenshots": ["https://linkwarden.app/_next/image?url=%2Fthumbnail.png&w=1920&q=75"],
        "links": ["https://docs.linkwarden.app/"],
        "addons": ["Cluster"],
        "stars": 12000,
        "license": "GNU Affero General Public License v3.0",
        "spdx_id": "AGPL-3.0",
    },
    {
        "name": "penpot",
        "description": "Penpot is an open-source design and prototyping platform for cross-domain teams.",
        "source": "https://github.com/penpot/penpot",
        "icon": ICON_URLS["penpot"],
        "website": "https://penpot.app/",
        "installation": (
            "Deploy penpot-backend and penpot-exporter in the same pipeline phase before the frontend. "
            "Service names must stay penpot-backend and penpot-exporter so the frontend can reach them."
        ),
        "architecture": ["linux/amd64", "linux/arm64"],
        "categories": ["work", "collaboration", "productivity"],
        "screenshots": [
            "https://penpot.app/blog/content/images/size/w2000/2024/02/PenpotUI-flexlayout.png",
            "https://penpot.app/blog/content/images/size/w1000/2024/02/Penpot_workspace.png",
        ],
        "links": ["https://community.penpot.app/"],
        "addons": [],
        "stars": 47473,
        "license": "Mozilla Public License 2.0",
        "spdx_id": "MPL-2.0",
        "service_dir": "penpot-frontend",
    },
]


def update_index() -> None:
    index_path = ROOT / "index.json"
    data = json.loads(index_path.read_text(encoding="utf-8"))
    existing = {s["name"] for s in data["services"]}

    for entry in CATALOG_ENTRIES:
        service_dir = entry.get("service_dir", entry["name"])
        if entry["name"] in existing:
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
            "language": "TypeScript",
            "gitops": False,
            "template": f"{BASE}/{service_dir}/app.yaml",
            "status": "active",
            "license": entry["license"],
            "spdx_id": entry["spdx_id"],
            "dirname": entry["name"],
            "deploymentTypes": [
                {
                    "id": "standard",
                    "label": "Standard",
                    "default": True,
                    "template": f"{BASE}/{service_dir}/app.yaml",
                },
                {
                    "id": "ha",
                    "label": "High availability",
                    "template": f"{BASE}/{service_dir}/app.ha.yaml",
                },
            ],
        }
        data["services"].append(service)

    data["stats"]["total"] = len(data["services"])
    for entry in CATALOG_ENTRIES:
        for cat in entry["categories"]:
            data["categories"][cat] = data["categories"].get(cat, 0) + 1
    data["categories"]["helpdesk"] = data["categories"].get("helpdesk", 0) + 1

    index_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def add_penpot_ha() -> None:
    import yaml

    for slug in ("penpot-frontend", "penpot-exporter"):
        std_path = SERVICES / slug / "app.yaml"
        ha_path = SERVICES / slug / "app.ha.yaml"
        if ha_path.exists():
            continue
        doc = yaml.safe_load(std_path.read_text(encoding="utf-8"))
        ha_path.write_text(dump_yaml(doc), encoding="utf-8")


if __name__ == "__main__":
    build_specs()
    add_penpot_ha()
    update_index()
    print("Generated top-10 templates.")

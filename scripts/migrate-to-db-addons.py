#!/usr/bin/env python3
"""Migrate stack-templates from embedded SQLite to operator DB add-ons."""
from __future__ import annotations

import copy
import importlib.util
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "services"

_spec = importlib.util.spec_from_file_location(
    "gen_top10", Path(__file__).parent / "generate-top10-templates.py"
)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)


def pg_addon(name: str, password: str, instances: int) -> dict:
    a = gen.pg_addon(name, name, name, password, instances)
    a["resourceDefinitions"]["Cluster"]["spec"]["bootstrap"]["initdb"]["postInitApplicationSQL"] = [
        f"GRANT ALL ON SCHEMA public TO {name}",
        f"GRANT CREATE ON SCHEMA public TO {name}",
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {name}",
    ]
    return a


def mariadb_addon(name: str, password: str, replicas: int, galera: bool) -> dict:
    return gen.mariadb_addon(name, name, name, password, replicas, galera)


def documentdb_addon(name: str, password: str, nodes: int) -> dict:
    return gen.documentdb_addon(name, "mongoadmin", password, nodes)


def pg_host(name: str) -> str:
    return f"{name}-postgresql-rw"


def mysql_host(name: str) -> str:
    return f"{name}-mysql"


# slug -> migration spec
MIGRATIONS: dict[str, dict] = {
    "wikijs": {
        "db": "postgres",
        "remove_volumes": {"wikijs-data"},
        "remove_env": {"DB_TYPE", "DB_FILEPATH"},
        "set_env": {
            "DB_TYPE": "postgres",
            "DB_HOST": pg_host("wikijs"),
            "DB_PORT": "5432",
            "DB_NAME": "wikijs",
            "DB_USER": "wikijs",
            "DB_PASS": "wikijs",
            "DB_SSL": "false",
        },
    },
    "directus": {
        "db": "postgres",
        "remove_volumes": {"directus-db-volume"},
        "remove_env": {"DB_CLIENT", "DB_FILENAME"},
        "set_env": {
            "DB_CLIENT": "pg",
            "DB_HOST": pg_host("directus"),
            "DB_PORT": "5432",
            "DB_DATABASE": "directus",
            "DB_USER": "directus",
            "DB_PASSWORD": "directus",
        },
    },
    "doccano": {
        "db": "postgres",
        "remove_volumes": set(),
        "remove_env": {"DATABASE_URL"},
        "set_env": {
            "DATABASE_URL": f"postgresql://doccano:doccano@{pg_host('doccano')}:5432/doccano",
        },
    },
    "lychee": {
        "db": "mariadb",
        "remove_volumes": {"lychee-db-volume"},
        "remove_env": {"DB_CONNECTION", "DB_DATABASE"},
        "set_env": {
            "DB_CONNECTION": "mysql",
            "DB_HOST": mysql_host("lychee"),
            "DB_PORT": "3306",
            "DB_DATABASE": "lychee",
            "DB_USERNAME": "lychee",
            "DB_PASSWORD": "lychee",
        },
        "command": [
            "sh",
            "-c",
            "mkdir -p /app/public/uploads && chown -R 1000:1000 /app/public/uploads "
            "&& chmod 0775 /app/public/uploads && "
            "until mysqladmin ping -h\"$DB_HOST\" -P\"$DB_PORT\" -u\"$DB_USERNAME\" -p\"$DB_PASSWORD\" --silent; do sleep 3; done && "
            "exec /usr/local/bin/entrypoint.sh php artisan octane:start --server=frankenphp --host=0.0.0.0 --port=8000",
        ],
    },
    "focalboard": {
        "db": "postgres",
        "remove_volumes": set(),
        "remove_env": set(),
        "set_env": {},
        "command": [
            "sh",
            "-c",
            'mkdir -p /opt/focalboard/data/files && printf \'%s\\n\' '
            '"{\\"serverRoot\\":\\"${FOCALBOARD_SERVER_ROOT}\\",\\"port\\":8000,'
            '\\"dbtype\\":\\"postgres\\",'
            f'\\"dbconfig\\":\\"host={pg_host("focalboard")} port=5432 user=focalboard password=focalboard dbname=focalboard sslmode=disable\\",'
            '\\"postgres_dbconfig\\":\\"dbname=focalboard sslmode=disable\\",'
            '\\"useSSL\\":false,\\"webpath\\":\\"./pack\\",\\"filespath\\":\\"./data/files\\",'
            '\\"telemetry\\":false,\\"session_expire_time\\":2592000,\\"session_refresh_time\\":18000,'
            '\\"localOnly\\":false,\\"enableLocalMode\\":true,'
            '\\"localModeSocketLocation\\":\\"/var/tmp/focalboard_local.socket\\",'
            '\\"enablePublicSharedBoards\\":false}" '
            "> /opt/focalboard/config.json && exec /opt/focalboard/bin/focalboard-server",
        ],
    },
    "headscale": {
        "db": "postgres",
        "remove_volumes": set(),
        "remove_env": {"HEADSCALE_DATABASE_SQLITE_PATH"},
        "set_env": {
            "HEADSCALE_DATABASE_TYPE": "postgres",
            "HEADSCALE_DATABASE_POSTGRES_HOST": pg_host("headscale"),
            "HEADSCALE_DATABASE_POSTGRES_PORT": "5432",
            "HEADSCALE_DATABASE_POSTGRES_NAME": "headscale",
            "HEADSCALE_DATABASE_POSTGRES_USER": "headscale",
            "HEADSCALE_DATABASE_POSTGRES_PASS": "headscale",
        },
        "install_note": (
            "PostgreSQL is provisioned via the bundled add-on. "
            "HEADSCALE_SERVER_URL must be the public HTTPS URL of this app. "
            "After deploy, create a user with headscale users create <name> "
            "(exec into the container or use the gRPC API). Generate a pre-auth key "
            "with headscale preauthkeys create --user <name> --reusable, then use it "
            "with the Tailscale client: tailscale up --login-server={{KUBERO_APP_URL}}."
        ),
    },
    "openobserve": {
        "db": "postgres",
        "remove_volumes": set(),
        "remove_env": {"ZO_META_STORE"},
        "set_env": {
            "ZO_META_STORE": "postgres",
            "ZO_META_POSTGRES_DSN": f"postgresql://openobserve:openobserve@{pg_host('openobserve')}:5432/openobserve",
        },
        "install_note": (
            "Metadata is stored in the bundled PostgreSQL add-on; ingest data persists "
            "under /data. Set ZO_ROOT_USER_EMAIL and ZO_ROOT_USER_PASSWORD before first "
            "login."
        ),
    },
    "shlink": {
        "db": "mariadb",
        "remove_volumes": set(),
        "remove_env": set(),
        "set_env": {
            "DB_DRIVER": "mysql",
            "DB_NAME": "shlink",
            "DB_USER": "shlink",
            "DB_PASSWORD": "shlink",
            "DB_HOST": mysql_host("shlink"),
            "DB_PORT": "3306",
        },
        "install_note": "Uses the MariaDB add-on. Set DEFAULT_DOMAIN to your short domain.",
    },
    "gitea": {
        "db": "postgres",
        "remove_volumes": set(),
        "remove_env": set(),
        "set_env": {
            "GITEA__database__DB_TYPE": "postgres",
            "GITEA__database__HOST": pg_host("gitea"),
            "GITEA__database__PORT": "5432",
            "GITEA__database__NAME": "gitea",
            "GITEA__database__USER": "gitea",
            "GITEA__database__PASSWD": "gitea",
        },
    },
    "forgejo": {
        "db": "postgres",
        "remove_volumes": set(),
        "remove_env": set(),
        "set_env": {
            "FORGEJO__database__DB_TYPE": "postgres",
            "FORGEJO__database__HOST": pg_host("forgejo"),
            "FORGEJO__database__PORT": "5432",
            "FORGEJO__database__NAME": "forgejo",
            "FORGEJO__database__USER": "forgejo",
            "FORGEJO__database__PASSWD": "forgejo",
        },
    },
    "fief": {
        "db": "postgres",
        "remove_volumes": {"fief-db-volume"},
        "remove_env": set(),
        "set_env": {
            "DATABASE_URL": f"postgresql+asyncpg://fief:fief@{pg_host('fief')}:5432/fief",
        },
    },
    "nocodb": {
        "db": "postgres",
        "remove_volumes": {"nocodb-data-volume"},
        "remove_env": set(),
        "set_env": {
            "NC_DB": "pg",
            "NC_DB_HOST": pg_host("nocodb"),
            "NC_DB_PORT": "5432",
            "NC_DB_USER": "nocodb",
            "NC_DB_PASSWORD": "nocodb",
            "NC_DB_DATABASE_NAME": "nocodb",
        },
    },
    "linkding": {
        "db": "postgres",
        "remove_volumes": {"linkding-data"},
        "remove_env": set(),
        "set_env": {
            "LD_DB_ENGINE": "postgres",
            "LD_DB_HOST": pg_host("linkding"),
            "LD_DB_PORT": "5432",
            "LD_DB_DATABASE": "linkding",
            "LD_DB_USER": "linkding",
            "LD_DB_PASSWORD": "linkding",
        },
    },
    "wallabag": {
        "db": "mariadb",
        "remove_volumes": {"wallabag-data"},
        "remove_env": set(),
        "set_env": {
            "SYMFONY__ENV__DATABASE_DRIVER": "pdo_mysql",
            "SYMFONY__ENV__DATABASE_HOST": mysql_host("wallabag"),
            "SYMFONY__ENV__DATABASE_PORT": "3306",
            "SYMFONY__ENV__DATABASE_NAME": "wallabag",
            "SYMFONY__ENV__DATABASE_USER": "wallabag",
            "SYMFONY__ENV__DATABASE_PASSWORD": "wallabag",
        },
    },
    "kanboard": {
        "db": "mariadb",
        "remove_volumes": {"kanboard-data-volume"},
        "remove_env": set(),
        "set_env": {
            "DB_DRIVER": "mysql",
            "DB_USERNAME": "kanboard",
            "DB_PASSWORD": "kanboard",
            "DB_NAME": "kanboard",
            "DB_HOSTNAME": mysql_host("kanboard"),
        },
    },
    "vaultwarden": {
        "db": "postgres",
        "remove_volumes": set(),
        "remove_env": set(),
        "set_env": {
            "DATABASE_URL": f"postgresql://vaultwarden:vaultwarden@{pg_host('vaultwarden')}:5432/vaultwarden",
        },
    },
    "uptime-kuma": {
        "db": "mariadb",
        "remove_volumes": {"uptime-kuma-data"},
        "remove_env": set(),
        "set_env": {
            "DB_TYPE": "mariadb",
            "DB_MYSQL_HOST": mysql_host("uptimekuma"),
            "DB_MYSQL_PORT": "3306",
            "DB_MYSQL_USER": "uptimekuma",
            "DB_MYSQL_PASSWORD": "uptimekuma",
            "DB_MYSQL_DATABASE": "uptimekuma",
        },
    },
    "memos": {
        "db": "postgres",
        "remove_volumes": {"memos-data"},
        "remove_env": set(),
        "set_env": {
            "MEMOS_DRIVER": "postgres",
            "MEMOS_DSN": f"postgresql://memos:memos@{pg_host('memos')}:5432/memos",
        },
    },
    "erugo": {
        "db": "mariadb",
        "remove_volumes": set(),
        "remove_env": set(),
        "set_env": {
            "DB_CONNECTION": "mysql",
            "DB_HOST": mysql_host("erugo"),
            "DB_PORT": "3306",
            "DB_DATABASE": "erugo",
            "DB_USERNAME": "erugo",
            "DB_PASSWORD": "erugo",
        },
    },
    "gotify": {
        "db": "postgres",
        "remove_volumes": set(),
        "remove_env": set(),
        "set_env": {
            "GOTIFY_DATABASE_DIALECT": "postgres",
            "GOTIFY_DATABASE_HOST": pg_host("gotify"),
            "GOTIFY_DATABASE_PORT": "5432",
            "GOTIFY_DATABASE_USER": "gotify",
            "GOTIFY_DATABASE_PASSWORD": "gotify",
            "GOTIFY_DATABASE_NAME": "gotify",
        },
    },
    "anythingllm": {
        "db": "postgres",
        "remove_volumes": set(),
        "remove_env": set(),
        "set_env": {
            "DATABASE_URL": f"postgresql://anythingllm:anythingllm@{pg_host('anythingllm')}:5432/anythingllm",
        },
    },
    "countly": {
        "db": "documentdb",
        "remove_volumes": {"countly-mongodb"},
        "remove_env": {"COUNTLY_MONGO_INSIDE"},
        "set_env": {
            "COUNTLY_CONFIG__MONGODB": gen.documentdb_uri(
                "countly-documentdb", "mongoadmin", "countly", "countly"
            ),
        },
        "clear_command": True,
        "install_note": (
            "Countly Community Edition (countly/countly-server:23.11.22) with the "
            "DocumentDB add-on for analytics storage. Pin to 23.11.22 — Countly 25.x "
            "needs MongoDB 8 features this add-on may lack. Requires at least 2Gi RAM; "
            "first boot can take several minutes. FIRST-RUN: open the site, complete the "
            "setup wizard to create the global admin account, then add your first "
            "application for its App Key/API Key. The appimages volume keeps uploaded "
            "app icons/avatars."
        ),
    },
    # --- batch 2: apps that default to SQLite but support operator DB add-ons ---
    "homarr": {
        "db": "postgres",
        "image_repo": "ghcr.io/homarr-labs/homarr",
        "image_tag": "latest",
        "replace_volumes": [
            {
                "accessModes": ["ReadWriteMany"],
                "emptyDir": False,
                "mountPath": "/appdata",
                "name": "homarr-appdata",
                "size": "1Gi",
                "storageClass": "shared",
            },
        ],
        "set_env": {
            "DB_DRIVER": "node-postgres",
            "DB_HOST": pg_host("homarr"),
            "DB_PORT": "5432",
            "DB_NAME": "homarr",
            "DB_USER": "homarr",
            "DB_PASSWORD": "homarr",
        },
        "install_note": (
            "Uses Homarr v1 (homarr-labs) with the bundled PostgreSQL add-on. "
            "Set AUTH_SECRET and SECRET_ENCRYPTION_KEY to random values before production use."
        ),
        "metadata_source": "https://github.com/homarr-labs/homarr",
    },
    "homebox": {
        "db": "postgres",
        "set_env": {
            "HBOX_DATABASE_DRIVER": "postgres",
            "HBOX_DATABASE_HOST": pg_host("homebox"),
            "HBOX_DATABASE_PORT": "5432",
            "HBOX_DATABASE_USERNAME": "homebox",
            "HBOX_DATABASE_PASSWORD": "homebox",
            "HBOX_DATABASE_DATABASE": "homebox",
            "HBOX_DATABASE_SSL_MODE": "disable",
        },
    },
    "twofauth": {
        "db": "mariadb",
        "remove_volumes": {"twofauth-volume"},
        "set_env": {
            "DB_CONNECTION": "mysql",
            "DB_HOST": mysql_host("twofauth"),
            "DB_PORT": "3306",
            "DB_DATABASE": "twofauth",
            "DB_USERNAME": "twofauth",
            "DB_PASSWORD": "twofauth",
            "APP_ENV": "production",
        },
    },
    "flowise": {
        "db": "postgres",
        "set_env": {
            "DATABASE_TYPE": "postgres",
            "DATABASE_HOST": pg_host("flowise"),
            "DATABASE_PORT": "5432",
            "DATABASE_NAME": "flowise",
            "DATABASE_USER": "flowise",
            "DATABASE_PASSWORD": "flowise",
        },
    },
    "docuseal": {
        "db": "postgres",
        "append_volumes": [
            {
                "accessModes": ["ReadWriteMany"],
                "emptyDir": False,
                "mountPath": "/data",
                "name": "docuseal-data",
                "size": "2Gi",
                "storageClass": "shared",
            },
        ],
        "set_env": {
            "DATABASE_URL": f"postgresql://docuseal:docuseal@{pg_host('docuseal')}:5432/docuseal",
        },
    },
    "shiori": {
        "db": "postgres",
        "append_volumes": [
            {
                "accessModes": ["ReadWriteMany"],
                "emptyDir": False,
                "mountPath": "/srv/shiori",
                "name": "shiori-data",
                "size": "2Gi",
                "storageClass": "shared",
            },
        ],
        "set_env": {
            "SHIORI_DIR": "/srv/shiori",
            "SHIORI_DATABASE_URL": (
                f"postgres://shiori:shiori@{pg_host('shiori')}:5432/shiori?sslmode=disable"
            ),
            "SHIORI_HTTP_SECRET_KEY": "change-me-to-a-random-string",
        },
        "command": ["sh", "-c", "shiori migrate && exec shiori serve"],
    },
    "opengist": {
        "db": "postgres",
        "set_env": {
            "OG_DB_URI": f"postgres://opengist:opengist@{pg_host('opengist')}:5432/opengist?sslmode=disable",
        },
    },
}


def merge_env(existing: list, remove: set[str], set_vals: dict[str, str]) -> list:
    out = [e for e in existing if e.get("name") not in remove and e.get("name") not in set_vals]
    for k, v in set_vals.items():
        out.append({"name": k, "value": v})
    return out


def db_id(slug: str) -> str:
    return slug.replace("-", "")


def apply_migration(path: Path, ha: bool) -> bool:
    slug = path.parent.name
    mig = MIGRATIONS.get(slug)
    if not mig:
        return False

    doc = yaml.safe_load(path.read_text()) or {}
    spec = doc.setdefault("spec", {})
    pwd = db_id(slug)
    db = db_id(slug)

    if mig["db"] == "postgres":
        spec["addons"] = [pg_addon(db, pwd, 3 if ha else 1)]
    elif mig["db"] == "mariadb":
        spec["addons"] = [mariadb_addon(db, pwd, 3 if ha else 1, ha)]
    elif mig["db"] == "documentdb":
        spec["addons"] = [documentdb_addon(db, pwd, 3 if ha else 1)]

    spec["envVars"] = merge_env(
        spec.get("envVars") or [],
        mig.get("remove_env") or set(),
        mig.get("set_env") or {},
    )

    if mig.get("replace_volumes") is not None:
        spec["extraVolumes"] = copy.deepcopy(mig["replace_volumes"])
    else:
        remove_vols = mig.get("remove_volumes") or set()
        if remove_vols:
            spec["extraVolumes"] = [
                v for v in (spec.get("extraVolumes") or [])
                if v.get("name") not in remove_vols
            ]
        if mig.get("append_volumes"):
            spec.setdefault("extraVolumes", []).extend(copy.deepcopy(mig["append_volumes"]))

    img = spec.setdefault("image", {})
    if mig.get("image_repo"):
        img["repository"] = mig["image_repo"]
    if mig.get("image_tag"):
        img["tag"] = mig["image_tag"]
    if mig.get("command"):
        img["command"] = mig["command"]
    if mig.get("clear_command"):
        img.pop("command", None)

    if mig.get("metadata_source"):
        ann = doc.setdefault("metadata", {}).setdefault("annotations", {})
        ann["kubero.dev/template.source"] = mig["metadata_source"]

    if mig.get("install_note"):
        ann = doc.setdefault("metadata", {}).setdefault("annotations", {})
        ann["kubero.dev/template.installation"] = mig["install_note"]

    # Strip sqlite mentions from installation text when present
    ann = doc.get("metadata", {}).get("annotations") or {}
    inst = ann.get("kubero.dev/template.installation") or ""
    if inst and re.search(r"\bsqlite\b", inst, re.I):
        ann["kubero.dev/template.installation"] = re.sub(
            r"[^.]*\bsqlite\b[^.]*\.?\s*",
            "Database is provisioned via the bundled add-on. ",
            inst,
            count=1,
            flags=re.I,
        )

    path.write_text(yaml.dump(doc, default_flow_style=False, sort_keys=False, allow_unicode=True))
    return True


def main() -> int:
    changed = []
    for slug in MIGRATIONS:
        for name in ("app.yaml", "app.ha.yaml"):
            path = SERVICES / slug / name
            if path.exists():
                if apply_migration(path, ha=(name == "app.ha.yaml")):
                    changed.append(str(path))

    print(f"Migrated {len(changed)} files:")
    for p in changed:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Assemble Kubero templates from researched JSON specs in scripts/_specs/.

Reads every scripts/_specs/<slug>.json (written by the gen-templates workflow),
emits services/<slug>/app.yaml + app.ha.yaml using the repo's standard helper
conventions, and appends index.json entries (maintaining stats + categories).

Standard vs HA: same app spec; only the operator add-ons scale.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "services"
SPECS = Path(__file__).resolve().parent / "_specs"
BASE = "https://raw.githubusercontent.com/stackblaze/stack-templates/main/services"

# Reuse the canonical helpers from generate-top10-templates.py
_spec = importlib.util.spec_from_file_location(
    "gen_top10", Path(__file__).parent / "generate-top10-templates.py"
)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

pg_addon = gen.pg_addon
mariadb_addon = gen.mariadb_addon
valkey_addon = gen.valkey_addon
documentdb_addon = gen.documentdb_addon
clickhouse_addon = gen.clickhouse_addon
template_doc = gen.template_doc
dump_yaml = gen.dump_yaml


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
                    "persistence": {"storageClassName": "fast", "storage": "1Gi"},
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
                    "default_user.conf": f"default_user = {user}\ndefault_pass = {password}",
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


def build_addon(a: dict, slug: str, ha: bool) -> dict | None:
    t = str(a.get("type", "")).strip().lower()
    name = a.get("name") or slug
    db = a.get("db") or slug
    user = a.get("user") or slug
    pw = a.get("password") or slug
    if t in ("postgres", "postgresql", "pg", "cnpg", "cluster"):
        return pg_addon(name, db, user, pw, 3 if ha else 1)
    if t in ("mariadb", "mysql"):
        return mariadb_addon(name, db, user, pw, 3 if ha else 1, ha)
    if t in ("valkey", "redis"):
        return valkey_addon(name, ha)
    if t in ("documentdb", "mongodb", "mongo"):
        return documentdb_addon(name, a.get("user") or "mongoadmin", pw, 3 if ha else 1)
    if t in ("clickhouse",):
        return clickhouse_addon(name, pw, 2 if ha else 1)
    if t in ("rabbitmq", "rabbit"):
        return rabbitmq_addon(name, user, pw, 3 if ha else 1)
    if t in ("memcached",):
        return memcached_addon(name, 2 if ha else 1)
    return None


def norm_volume(v: dict, slug: str) -> dict:
    out = {
        "accessModes": [v.get("accessMode", "ReadWriteOnce")],
        "emptyDir": False,
        "mountPath": v["mountPath"],
        "name": v.get("name") or f"{slug}-data",
        "size": str(v.get("size", "2Gi")),
    }
    if v.get("storageClass"):
        out["storageClass"] = v["storageClass"]
    return out


def norm_image(img: dict) -> dict:
    out = {
        "containerPort": str(img.get("containerPort", "80")),
        "pullPolicy": "Always",
        "repository": img["repository"],
        "tag": str(img.get("tag", "latest")),
    }
    cmd = img.get("command")
    if cmd:
        out["command"] = cmd
    return out


def clean_url(u: str) -> str:
    u = (u or "").strip()
    return u.split()[0] if " " in u else u


def make_spec(spec: dict, ha: bool) -> dict:
    slug = spec["slug"]
    addons = []
    for a in spec.get("addons") or []:
        built = build_addon(a, slug, ha)
        if built:
            addons.append(built)
    envvars = [
        {"name": e["name"], "value": str(e.get("value", ""))}
        for e in (spec.get("envVars") or [])
        if e.get("name")
    ]
    volumes = [norm_volume(v, slug) for v in (spec.get("extraVolumes") or []) if v.get("mountPath")]
    return template_doc(
        slug,
        spec.get("title", slug),
        spec.get("description", "").strip(),
        clean_url(spec.get("icon", "")),
        spec.get("source", ""),
        spec.get("website", ""),
        [c.strip() for c in (spec.get("categories") or []) if c.strip()],
        spec.get("installation", "").strip(),
        [clean_url(s) for s in (spec.get("screenshots") or []) if s],
        [clean_url(l) for l in (spec.get("links") or []) if l],
        {
            "deploymentstrategy": "docker",
            "addons": addons,
            "envVars": envvars,
            "extraVolumes": volumes,
            "cronjobs": [],
            "web": {"replicaCount": 1},
            "worker": {"replicaCount": 0},
            "image": norm_image(spec["image"]),
        },
    )


REQUIRED = ("slug", "title", "image")


def load_specs() -> list[dict]:
    specs = []
    errors = []
    for p in sorted(SPECS.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{p.name}: bad JSON ({exc})")
            continue
        missing = [k for k in REQUIRED if not d.get(k)]
        if missing:
            errors.append(f"{p.name}: missing {missing}")
            continue
        if not (d.get("image") or {}).get("repository"):
            errors.append(f"{p.name}: image.repository missing")
            continue
        specs.append(d)
    if errors:
        print("SPEC ISSUES (skipped):")
        for e in errors:
            print("  -", e)
    return specs


def lint_addon_hosts(spec: dict) -> list[str]:
    """Warn if an add-on's expected host is not referenced by any env var."""
    slug = spec["slug"]
    env_blob = " ".join(str(e.get("value", "")) for e in (spec.get("envVars") or []))
    hosts = {
        "postgres": f"{slug}-postgresql-rw",
        "mariadb": f"{slug}-mysql",
        "valkey": f"rfr-{slug}-valkey-readwrite",
        "documentdb": f"documentdb-service-{slug}-documentdb",
        "clickhouse": f"clickhouse-{slug}-clickhouse",
        "rabbitmq": f"{slug}-rabbitmq",
        "memcached": f"{slug}-memcached",
    }
    warns = []
    for a in spec.get("addons") or []:
        t = str(a.get("type", "")).lower()
        name = a.get("name") or slug
        key = {
            "postgresql": "postgres", "pg": "postgres", "cluster": "postgres",
            "mysql": "mariadb", "redis": "valkey", "mongodb": "documentdb", "mongo": "documentdb",
        }.get(t, t)
        host = hosts.get(key, "").replace(slug, name)
        if host and host not in env_blob:
            warns.append(f"{slug}: add-on {t} host '{host}' not referenced in envVars")
    return warns


def index_entry(spec: dict) -> dict:
    slug = spec["slug"]
    stars = int(spec.get("stars") or 0)
    addon_kinds = []
    for a in spec.get("addons") or []:
        t = str(a.get("type", "")).lower()
        addon_kinds.append({
            "postgres": "Cluster", "postgresql": "Cluster", "pg": "Cluster", "cluster": "Cluster",
            "mariadb": "MariaDB", "mysql": "MariaDB", "valkey": "Valkey", "redis": "Valkey",
            "documentdb": "DocumentDB", "mongodb": "DocumentDB", "mongo": "DocumentDB",
            "clickhouse": "ClickHouseInstallation", "rabbitmq": "RabbitmqCluster",
            "memcached": "KuberoAddonMemcached",
        }.get(t, t))
    return {
        "name": slug,
        "description": spec.get("description", "").strip(),
        "source": spec.get("source", ""),
        "icon": clean_url(spec.get("icon", "")),
        "website": spec.get("website", ""),
        "installation": spec.get("installation", "").strip(),
        "architecture": [],
        "categories": [c.strip() for c in (spec.get("categories") or []) if c.strip()],
        "screenshots": [clean_url(s) for s in (spec.get("screenshots") or []) if s],
        "links": [clean_url(l) for l in (spec.get("links") or []) if l],
        "addons": addon_kinds,
        "stars": stars,
        "forks": max(stars // 10, 1),
        "watchers": stars,
        "issues": 0,
        "last_updated": "2026-06-13T00:00:00Z",
        "last_pushed": "2026-06-13T00:00:00Z",
        "created_at": "2020-01-01T00:00:00Z",
        "size": 0,
        "language": spec.get("language", "TypeScript"),
        "gitops": False,
        "template": f"{BASE}/{slug}/app.yaml",
        "status": "active",
        "license": spec.get("license", "Other"),
        "spdx_id": spec.get("spdx_id", "NOASSERTION"),
        "dirname": slug,
        "deploymentTypes": [
            {"id": "standard", "label": "Standard", "default": True, "template": f"{BASE}/{slug}/app.yaml"},
            {"id": "ha", "label": "High availability", "template": f"{BASE}/{slug}/app.ha.yaml"},
        ],
    }


def main() -> int:
    specs = load_specs()
    print(f"\nLoaded {len(specs)} valid specs")

    # Write template pairs
    warns = []
    written = []
    for spec in specs:
        slug = spec["slug"]
        folder = SERVICES / slug
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "app.yaml").write_text(dump_yaml(make_spec(spec, False)), encoding="utf-8")
        (folder / "app.ha.yaml").write_text(dump_yaml(make_spec(spec, True)), encoding="utf-8")
        warns.extend(lint_addon_hosts(spec))
        written.append(slug)

    # Update index.json
    index_path = ROOT / "index.json"
    data = json.loads(index_path.read_text(encoding="utf-8"))
    existing = {s["name"] for s in data["services"]}
    added = 0
    for spec in specs:
        if spec["slug"] in existing:
            continue
        entry = index_entry(spec)
        data["services"].append(entry)
        for cat in entry["categories"]:
            data["categories"][cat] = data["categories"].get(cat, 0) + 1
        data.setdefault("stats", {})
        data["stats"]["stars"] = data["stats"].get("stars", 0) + entry["stars"]
        added += 1

    data["stats"]["total"] = len(data["services"])
    data["stats"]["categories"] = len(data["categories"])
    index_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Wrote {len(written)} template pairs; appended {added} new index entries.")
    print(f"index.json now has {len(data['services'])} services.")
    if warns:
        print(f"\nADD-ON HOST WARNINGS ({len(warns)}):")
        for w in warns:
            print("  -", w)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

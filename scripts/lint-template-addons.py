#!/usr/bin/env python3
"""Fail if any catalog template references a retired Kubero add-on kind."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "services"

# Keep in sync with kubero/server/src/addons/addon-tiers.ts DEPRECATED_ADDON_KINDS
RETIRED_KINDS = {
    "KuberoAddonPostgres",
    "KuberoAddonRedis",
    "KuberoAddonMysql",
    "KuberoAddonMongodb",
    "KuberoAddonRabbitmq",
    "PerconaServerMongoDB",
    "PostgresCluster",
    "WeaviateCluster",
    "KuberoMail",
    "Elasticsearch",
    "Redis",
    "RedisCluster",
}

REPLACEMENTS = {
    "KuberoAddonPostgres": "Cluster",
    "KuberoAddonRedis": "Valkey",
    "KuberoAddonMysql": "MariaDB",
    "KuberoAddonMongodb": "DocumentDB",
    "KuberoAddonRabbitmq": "RabbitmqCluster",
    "PerconaServerMongoDB": "DocumentDB",
    "PostgresCluster": "Cluster",
    "WeaviateCluster": "Milvus",
    "Elasticsearch": "KuberoOpenSearch",
    "Redis": "Valkey",
    "RedisCluster": "Valkey",
}


def check_file(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"{path}: failed to parse YAML ({exc})"]
    addons = (doc.get("spec") or {}).get("addons") or []
    for addon in addons:
        kind = str(addon.get("kind") or "").strip()
        if kind in RETIRED_KINDS:
            repl = REPLACEMENTS.get(kind, "a supported operator add-on")
            errors.append(f"{path}: retired add-on {kind} — use {repl}")
    return errors


def main() -> int:
    errors: list[str] = []
    for path in sorted(SERVICES.glob("*/app*.yaml")):
        errors.extend(check_file(path))
    if errors:
        print("Retired add-on kinds found in templates:\n")
        for line in errors:
            print(f"  - {line}")
        return 1
    print(f"OK — no retired add-ons in {len(list(SERVICES.glob('*/app*.yaml')))} template files")
    return 0


if __name__ == "__main__":
    sys.exit(main())

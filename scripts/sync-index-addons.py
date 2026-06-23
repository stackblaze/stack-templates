#!/usr/bin/env python3
"""Sync index.json `addons` arrays from each template's app.yaml spec.addons.

The dashboard catalog reads index.json (enriched server-side into addonDetails).
Stale entries — e.g. metabase listing [] while app.yaml ships PostgreSQL — hide
bundled services from template cards. This script rewrites index.json in place.

Uses the standard variant (services/<slug>/app.yaml). When app.yaml is missing,
falls back to the URL in deploymentTypes[id=standard] or top-level `template`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.json"
SERVICES = ROOT / "services"

# Stable ordering for catalog pills (matches common UI priority).
KIND_ORDER = {
    "Cluster": 0,
    "MariaDB": 1,
    "DocumentDB": 2,
    "Valkey": 3,
    "KuberoAddonMemcached": 4,
    "RabbitmqCluster": 5,
    "Kafka": 6,
    "ClickHouseInstallation": 7,
    "KuberoOpenSearch": 8,
    "Milvus": 9,
    "ScyllaCluster": 10,
    "CassandraDatacenter": 11,
    "CrdbCluster": 12,
    "KuberoFerretDB": 13,
    "KuberoCouchDB": 14,
    "Tenant": 15,
}


def sort_kinds(kinds: list[str]) -> list[str]:
    return sorted(kinds, key=lambda k: (KIND_ORDER.get(k, 99), k))


def addon_kinds_from_yaml(path: Path) -> list[str]:
    if not path.is_file():
        return []
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"WARN: could not parse {path}: {exc}", file=sys.stderr)
        return []
    kinds: list[str] = []
    seen: set[str] = set()
    for addon in (doc.get("spec") or {}).get("addons") or []:
        kind = str(addon.get("kind") or "").strip()
        if not kind or kind in seen:
            continue
        seen.add(kind)
        kinds.append(kind)
    return sort_kinds(kinds)


def standard_app_yaml(service: dict) -> Path | None:
    dirname = (service.get("dirname") or service.get("name") or "").strip()
    if dirname:
        local = SERVICES / dirname / "app.yaml"
        if local.is_file():
            return local
    for dt in service.get("deploymentTypes") or []:
        if dt.get("id") == "standard" and dt.get("template"):
            url = str(dt["template"])
            # .../services/<slug>/app.yaml
            parts = urlparse(url).path.strip("/").split("/")
            if len(parts) >= 2 and parts[-1].endswith(".yaml"):
                slug = parts[-2]
                candidate = SERVICES / slug / parts[-1]
                if candidate.is_file():
                    return candidate
    template_url = service.get("template")
    if template_url:
        parts = urlparse(str(template_url)).path.strip("/").split("/")
        if len(parts) >= 2:
            candidate = SERVICES / parts[-2] / parts[-1]
            if candidate.is_file():
                return candidate
    return None


def merge_ha_kinds(service: dict, kinds: list[str]) -> list[str]:
    """Union HA template add-ons when app.ha.yaml declares extras."""
    dirname = (service.get("dirname") or service.get("name") or "").strip()
    ha_path = SERVICES / dirname / "app.ha.yaml" if dirname else None
    if ha_path and ha_path.is_file():
        extra = addon_kinds_from_yaml(ha_path)
        merged = list(dict.fromkeys([*kinds, *extra]))
        return sort_kinds(merged)
    return kinds


def main() -> int:
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    services = data.get("services") or []
    updated = 0
    missing_yaml = 0
    unchanged = 0

    for svc in services:
        path = standard_app_yaml(svc)
        if not path:
            missing_yaml += 1
            continue
        kinds = merge_ha_kinds(svc, addon_kinds_from_yaml(path))
        old = list(svc.get("addons") or [])
        if old == kinds:
            unchanged += 1
            continue
        name = svc.get("name") or svc.get("dirname") or "?"
        print(f"  {name}: {old or '[]'} -> {kinds or '[]'}")
        svc["addons"] = kinds
        updated += 1

    if updated:
        INDEX.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(
        f"\nDone: {updated} updated, {unchanged} already correct, "
        f"{missing_yaml} missing app.yaml, {len(services)} total"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Normalize every template to the Standard / HA variant contract:

  app.yaml (Standard)
    - web.replicaCount: 1
    - extraVolumes (non-emptyDir): ReadWriteOnce + storageClass slow
    - image.run.securityContext.readOnlyRootFilesystem: true
    - DB addons: single instance (CNPG instances=1, MariaDB replicas=1, galera off)

  app.ha.yaml (High availability)
    - web.replicaCount: max(2, prior web replicas) when web > 0
    - extraVolumes (non-emptyDir): ReadWriteMany + storageClass shared
    - image.run.securityContext.readOnlyRootFilesystem: false
    - DB addons: HA scale (instances/replicas = 3, galera on when present)

Also ensures index.json lists both deploymentTypes for every service with app.yaml.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "services"
INDEX = ROOT / "index.json"
GITHUB_RAW = (
    "https://raw.githubusercontent.com/stackblaze/stack-templates/main/services"
)


def load_yaml(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"WARN: parse failed {path}: {exc}", file=sys.stderr)
        return None


def dump_yaml(path: Path, doc: dict) -> None:
    path.write_text(
        yaml.dump(doc, default_flow_style=False, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def ensure_image_run_ro(doc: dict, read_only: bool) -> None:
    spec = doc.setdefault("spec", {})
    image = spec.setdefault("image", {})
    run = image.setdefault("run", {})
    sc = run.setdefault("securityContext", {})
    sc["readOnlyRootFilesystem"] = read_only


def normalize_volumes(spec: dict, variant: str) -> None:
    volumes = spec.get("extraVolumes") or []
    for vol in volumes:
        if not isinstance(vol, dict) or vol.get("emptyDir"):
            continue
        if variant == "standard":
            vol["accessModes"] = ["ReadWriteOnce"]
            vol["storageClass"] = "slow"
        else:
            vol["accessModes"] = ["ReadWriteMany"]
            vol["storageClass"] = "shared"
    spec["extraVolumes"] = volumes


def normalize_web_replicas(spec: dict, variant: str) -> None:
    web = spec.get("web")
    if not isinstance(web, dict):
        return
    current = int(web.get("replicaCount") or 0)
    if variant == "standard":
        if current > 0:
            web["replicaCount"] = 1
    else:
        if current > 0:
            web["replicaCount"] = max(2, current)
    spec["web"] = web


def scale_addon_tree(node: object, variant: str) -> None:
    if isinstance(node, dict):
        if "instances" in node and isinstance(node["instances"], int):
            node["instances"] = 1 if variant == "standard" else 3
        if "replicas" in node and isinstance(node["replicas"], int):
            node["replicas"] = 1 if variant == "standard" else 3
        if "galera" in node and isinstance(node["galera"], dict):
            node["galera"]["enabled"] = variant == "ha"
        for value in node.values():
            scale_addon_tree(value, variant)
    elif isinstance(node, list):
        for item in node:
            scale_addon_tree(item, variant)


def normalize_addons(spec: dict, variant: str) -> None:
    addons = spec.get("addons") or []
    for addon in addons:
        if isinstance(addon, dict):
            scale_addon_tree(addon.get("resourceDefinitions"), variant)
    spec["addons"] = addons


def apply_variant(doc: dict, variant: str) -> dict:
    out = copy.deepcopy(doc)
    spec = out.setdefault("spec", {})
    normalize_web_replicas(spec, variant)
    normalize_volumes(spec, variant)
    normalize_addons(spec, variant)
    ensure_image_run_ro(out, variant == "standard")
    return out


def ensure_index_deployment_types(data: dict, slug: str) -> bool:
    services = data.get("services") or []
    svc = next(
        (s for s in services if (s.get("dirname") or s.get("name")) == slug),
        None,
    )
    if not svc:
        return False
    standard_url = f"{GITHUB_RAW}/{slug}/app.yaml"
    ha_url = f"{GITHUB_RAW}/{slug}/app.ha.yaml"
    desired = [
        {
            "id": "standard",
            "label": "Standard",
            "default": True,
            "template": standard_url,
        },
        {"id": "ha", "label": "High availability", "template": ha_url},
    ]
    changed = False
    if svc.get("template") != standard_url:
        svc["template"] = standard_url
        changed = True
    if svc.get("deploymentTypes") != desired:
        svc["deploymentTypes"] = desired
        changed = True
    return changed


def main() -> int:
    index_data = json.loads(INDEX.read_text(encoding="utf-8"))
    index_changed = 0
    written_standard = 0
    written_ha = 0
    skipped = 0

    for app_yaml in sorted(SERVICES.glob("*/app.yaml")):
        slug = app_yaml.parent.name
        doc = load_yaml(app_yaml)
        if not doc:
            skipped += 1
            continue

        ha_path = app_yaml.parent / "app.ha.yaml"
        existing_ha = load_yaml(ha_path)

        standard_doc = apply_variant(doc, "standard")
        ha_source = existing_ha if existing_ha else doc
        ha_doc = apply_variant(ha_source, "ha")

        dump_yaml(app_yaml, standard_doc)
        dump_yaml(ha_path, ha_doc)
        written_standard += 1
        written_ha += 1

        if ensure_index_deployment_types(index_data, slug):
            index_changed += 1

    INDEX.write_text(
        json.dumps(index_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(
        f"Done: {written_standard} app.yaml, {written_ha} app.ha.yaml, "
        f"{index_changed} index deploymentTypes updated, {skipped} skipped"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

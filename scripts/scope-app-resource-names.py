#!/usr/bin/env python3
"""Scope app-owned Kubernetes resource names to {{KUBERO_APP_NAME}}."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

TOKEN = "{{KUBERO_APP_NAME}}"

RESOURCE_SUFFIXES = (
    "-postgresql",
    "-postgresql-app",
    "-postgresql-superuser",
    "-postgresql-rw",
    "-mariadb",
    "-mariadb-root",
    "-mariadb-app",
    "-mysql",
    "-mysql-root",
    "-mysql-app",
    "-valkey",
    "-redis",
    "-mongodb",
    "-mongo",
    "-opensearch",
    "-elasticsearch",
    "-es",
    "-kafka",
    "-clickhouse",
    "-db",
    "-db-app",
    "-db-root",
    "-db-superuser",
    "-db-rw",
    "-documentdb",
    "-shared",
    "-data",
    "-static",
    "-media",
    "-uploads",
    "-files",
    "-storage",
    "-assets",
    "-cache",
    "-config",
    "-logs",
    "-db-volume",
)

ENV_NAME_HINTS = re.compile(
    r"(HOST|URL|URI|SERVER|DATABASE|DB_|REDIS|POSTGRES|MYSQL|MARIA|"
    r"OPENSEARCH|ELASTIC|ES_|MONGO|VALKEY|KAFKA|CLICKHOUSE|S3_|BUCKET|"
    r"ENDPOINT)",
    re.I,
)

RESOURCE_NAME_RE = re.compile(
    r"^([a-z0-9][a-z0-9-]*)("
    + "|".join(re.escape(s) for s in RESOURCE_SUFFIXES)
    + r")$",
    re.I,
)

EMBEDDED_RESOURCE_RE = re.compile(
    r"([a-z0-9][a-z0-9-]*)(" + "|".join(re.escape(s) for s in RESOURCE_SUFFIXES) + r")"
)

STRING_KEYS = frozenset(
    {"name", "clusterName", "masterService", "value", "host", "url", "endpoint"}
)


def load_yaml(path: Path) -> dict | None:
    try:
        doc = yaml.safe_load(path.read_text())
    except yaml.YAMLError:
        return None
    return doc if isinstance(doc, dict) else None


def normalize_resource_token(value: str) -> str:
    if TOKEN in value:
        return value
    m = RESOURCE_NAME_RE.match(value)
    if m:
        return f"{TOKEN}{m.group(2)}"
    return value


def replace_slug_prefix(s: str, slug: str) -> str:
    if TOKEN in s or not slug:
        return s
    out = s
    for suffix in RESOURCE_SUFFIXES:
        needle = f"{slug}{suffix}"
        if needle in out:
            out = out.replace(needle, f"{TOKEN}{suffix}")
    return out


def replace_embedded_resources(s: str) -> str:
    if TOKEN in s or "github.com" in s or "raw.githubusercontent.com" in s:
        return s

    def sub(m: re.Match) -> str:
        return f"{TOKEN}{m.group(2)}"

    return EMBEDDED_RESOURCE_RE.sub(sub, s)


def transform_doc(doc: dict, slug: str) -> int:
    changes = 0

    def walk(node, path: tuple[str, ...] = ()):
        nonlocal changes
        if isinstance(node, dict):
            if (
                "name" in node
                and "value" in node
                and isinstance(node.get("name"), str)
                and isinstance(node.get("value"), str)
                and ENV_NAME_HINTS.search(node["name"])
            ):
                updated = replace_embedded_resources(
                    replace_slug_prefix(node["value"], slug)
                )
                if updated != node["value"]:
                    node["value"] = updated
                    changes += 1
            for key, value in node.items():
                new_path = path + (key,)
                if isinstance(value, str) and key in STRING_KEYS:
                    if new_path in (("metadata", "name"), ("spec", "name")):
                        continue
                    if key == "name":
                        updated = normalize_resource_token(
                            replace_slug_prefix(value, slug)
                        )
                    elif key in ("clusterName", "masterService"):
                        updated = normalize_resource_token(value)
                    elif key == "value" and ENV_NAME_HINTS.search(
                        str(node.get("name", ""))
                    ):
                        updated = replace_embedded_resources(
                            replace_slug_prefix(value, slug)
                        )
                    else:
                        updated = value
                    if updated != value:
                        node[key] = updated
                        changes += 1
                else:
                    walk(value, new_path)
            return
        if isinstance(node, list):
            for item in node:
                walk(item, path)

    walk(doc)
    return changes


def process_file(path: Path) -> int:
    doc = load_yaml(path)
    if not doc:
        return 0
    slug = path.parent.name
    changes = transform_doc(doc, slug)
    if changes:
        path.write_text(yaml.dump(doc, sort_keys=False, default_flow_style=False))
    return changes


def main() -> int:
    root = Path(__file__).resolve().parents[1] / "services"
    files = 0
    replacements = 0
    for path in sorted(root.rglob("app*.yaml")):
        n = process_file(path)
        if n:
            files += 1
            replacements += n
    print(f"Done: {files} files updated, {replacements} replacements")
    return 0


if __name__ == "__main__":
    sys.exit(main())

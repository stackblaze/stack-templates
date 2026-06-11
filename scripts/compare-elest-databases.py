#!/usr/bin/env python3
"""Compare Elest.io Databases & Cache vs Kubero add-on plugins."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

ELEST_CACHE = Path(os.environ.get("TEMP", "/tmp")) / "elest-catalog.html"

# Elest.io title (normalized) -> Kubero displayName(s) that cover it
ELEST_TO_KUBERO = {
    "postgresql": ["PostgreSQL (CloudNativePG)", "PostgreSQL", "Crunchy Postgres Cluster"],
    "postgres": ["PostgreSQL (CloudNativePG)", "PostgreSQL", "Crunchy Postgres Cluster"],
    "mariadb": ["MariaDB"],
    "mysql": ["MariaDB", "MySQL"],
    "mongodb": ["MongoDB", "Percona MongoDB", "Document DB"],
    "mongo": ["MongoDB", "Percona MongoDB", "Document DB"],
    "redis": ["Valkey", "Redis", "Opstree Redis", "Opstree Redis Cluster"],
    "valkey": ["Valkey"],
    "memcached": ["Memcached"],
    "rabbitmq": ["RabbitMQ"],
    "clickhouse": ["ClickHouse Cluster"],
    "opensearch": ["OpenSearch"],
    "elasticsearch": ["Elasticsearch", "OpenSearch"],
    "kafka": ["Kafka (Strimzi)"],
    "couchdb": ["CouchDB"],
    "cockroachdb": ["CockroachDB"],
    "cockroach": ["CockroachDB"],
    "ferretdb": ["FerretDB"],
    "minio": ["RustFS"],  # object storage — partial
    "meilisearch": [],  # no kubero addon
    "typesense": [],
    "solr": [],
    "influxdb": [],
    "timescaledb": ["PostgreSQL (CloudNativePG)"],  # extension on PG
    "pgvector": ["PostgreSQL (CloudNativePG)"],
    "rabbitmq": ["RabbitMQ"],
    "memcached": ["Memcached"],
    "milvus": ["Milvus"],
    "weaviate": ["Weaviate"],
    "chromadb": [],
    "chroma": [],
    "nats": [],
    "neo4j": [],
    "arangodb": [],
    "cassandra": [],
    "scylladb": [],
    "keydb": ["Valkey", "Redis"],
    "dragonfly": ["Valkey", "Redis"],
}


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def load_elest_databases() -> list[dict]:
    html = ELEST_CACHE.read_text(encoding="utf-8", errors="ignore")
    data = json.loads(re.search(r"var fullResponse = (\[.*?\]);", html).group(1))
    out = []
    for block in data:
        for t in block.get("templates", []):
            if t.get("category") == "Databases & Cache":
                out.append(t)
    return out


def kubero_addons() -> list[dict]:
    plugins_dir = Path(__file__).resolve().parents[2] / "kubero" / "server" / "src" / "addons" / "plugins"
    if not plugins_dir.exists():
        plugins_dir = Path(__file__).resolve().parents[2].parent / "kubero" / "server" / "src" / "addons" / "plugins"
    # stackblaze layout: stack-templates and kubero are siblings
    if not plugins_dir.exists():
        plugins_dir = Path(r"c:\Users\dean\Documents\stackblaze\kubero\server\src\addons\plugins")
    addons = []
    for f in sorted(plugins_dir.glob("*.ts")):
        if f.name.startswith("plugin"):
            continue
        text = f.read_text(encoding="utf-8")
        m_name = re.search(r"public displayName = '([^']+)'", text)
        m_kind = re.search(r"public (?:CRD)?kind = '([^']+)'", text)
        if not m_kind:
            m_kind = re.search(r'public id: string = [\'"]([^\'"]+)[\'"]', text)
        deprecated = "deprecated: boolean = true" in text
        if m_name:
            addons.append({
                "displayName": m_name.group(1),
                "kind": m_kind.group(1) if m_kind else "?",
                "file": f.stem,
                "deprecated": deprecated,
            })
    return addons


def match_elest(title: str, kubero_names: set[str]) -> tuple[bool, str]:
    n = norm(title)
    # direct keyword match
    for key, targets in ELEST_TO_KUBERO.items():
        if key in n or n in key:
            if targets:
                for t in targets:
                    if t in kubero_names:
                        return True, t
                return False, f"mapped but no plugin: {', '.join(targets)}"
            return False, "no Kubero add-on"
    # fuzzy: check if any kubero name token in title
    for kn in kubero_names:
        if norm(kn) in n or any(part in n for part in norm(kn).split() if len(part) > 4):
            return True, kn
    return False, "unmapped"


def main() -> None:
    elest = load_elest_databases()
    kubero = kubero_addons()
    active = [a for a in kubero if not a["deprecated"]]
    deprecated = [a for a in kubero if a["deprecated"]]
    names = {a["displayName"] for a in kubero}

    print("=" * 60)
    print(f"Elest.io 'Databases & Cache': {len(elest)} services")
    print(f"Kubero add-on plugins: {len(kubero)} total ({len(active)} active, {len(deprecated)} deprecated)")
    print("=" * 60)

    covered, missing = [], []
    for t in sorted(elest, key=lambda x: (x.get("title") or "").lower()):
        title = t.get("title") or ""
        ok, note = match_elest(title, names)
        row = {"title": title, "popular": t.get("isPopular"), "ok": ok, "note": note}
        (covered if ok else missing).append(row)

    print(f"\nCOVERED by Kubero add-on ({len(covered)}/{len(elest)}):")
    for r in covered:
        pop = " [popular]" if r["popular"] else ""
        print(f"  + {r['title']}{pop} -> {r['note']}")

    print(f"\nMISSING Kubero add-on ({len(missing)}/{len(elest)}):")
    for r in missing:
        pop = " [popular]" if r["popular"] else ""
        print(f"  - {r['title']}{pop} ({r['note']})")

    print("\nKubero add-ons NOT in Elest.io Databases & Cache catalog:")
    elest_norms = {norm(t.get("title") or "") for t in elest}
    extra = []
    for a in sorted(kubero, key=lambda x: x["displayName"]):
        dn = norm(a["displayName"])
        found = any(
            dn in en or en in dn
            or any(k in en for k in ELEST_TO_KUBERO if a["displayName"] in ELEST_TO_KUBERO[k])
            for en in elest_norms
        )
        if not found and a["displayName"] not in ("Cloudflare Tunnel", "RustFS", "Haraka Mail Server"):
            dep = " [deprecated]" if a["deprecated"] else ""
            extra.append(f"  * {a['displayName']}{dep} (kind: {a['kind']})")
    for line in extra:
        print(line)

    # stack-templates usage
    root = Path(__file__).resolve().parents[1]
    used_kinds: set[str] = set()
    import yaml

    for p in (root / "services").glob("*/app.yaml"):
        try:
            doc = yaml.safe_load(p.read_text(encoding="utf-8"))
            for addon in (doc.get("spec") or {}).get("addons") or []:
                if addon.get("kind"):
                    used_kinds.add(addon["kind"])
        except Exception:
            pass
    print(f"\nAdd-on kinds used in stack-templates ({len(used_kinds)}):")
    print(" ", ", ".join(sorted(used_kinds)))


if __name__ == "__main__":
    main()

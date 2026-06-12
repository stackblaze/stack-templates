#!/usr/bin/env python3
"""Generate the QA status table for README.md."""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
INDEX = ROOT / "index.json"
SERVICES = ROOT / "services"

MARKER_START = "<!-- qa-table:start -->"
MARKER_END = "<!-- qa-table:end -->"

# Kubero plugin `kind` → `displayName` (see kubero/server/src/addons/plugins/).
# Retired kinds (KuberoAddon*, PostgresCluster, PerconaServerMongoDB) must not appear
# in template YAML — see scripts/lint-template-addons.py.
KIND_DISPLAY = {
    "Cluster": "PostgreSQL (CloudNativePG)",
    "MariaDB": "MariaDB",
    "Valkey": "Valkey",
    "ClickHouseInstallation": "ClickHouse Cluster",
    "KuberoAddonMemcached": "Memcached",
    "KuberoMail": "Haraka Mail Server",
    "KuberoOpenSearch": "OpenSearch",
    "KuberoFerretDB": "FerretDB",
    "KuberoCouchDB": "CouchDB",
    "Elasticsearch": "Elasticsearch",
    "Kafka": "Kafka (Strimzi)",
    "DocumentDB": "Document DB",
    "RabbitmqCluster": "RabbitMQ",
    "Milvus": "Milvus",
    "WeaviateCluster": "Weaviate",
    "Tenant": "RustFS",
    "CrdbCluster": "CockroachDB",
}


def addon_labels(service: dict) -> list[str]:
    """Kubero add-on display names from template YAML (preferred) or index.json."""
    dirname = service.get("dirname") or service["name"]
    path = SERVICES / dirname / "app.yaml"
    labels: list[str] = []
    if path.exists():
        try:
            import yaml

            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
            for addon in (doc.get("spec") or {}).get("addons") or []:
                label = (addon.get("displayName") or "").strip()
                if not label:
                    kind = addon.get("kind") or ""
                    label = KIND_DISPLAY.get(kind, kind)
                if label and label not in labels:
                    labels.append(label)
        except Exception:
            labels = []
    if not labels:
        for kind in service.get("addons") or []:
            label = KIND_DISPLAY.get(kind, kind)
            if label and label not in labels:
                labels.append(label)
    return labels


def addons_cell(service: dict) -> str:
    labels = addon_labels(service)
    if not labels:
        return "—"
    return ", ".join(labels)


def ha_available(service: dict) -> bool:
    for dt in service.get("deploymentTypes") or []:
        if dt.get("id") == "ha":
            return True
    return False


def qa_cell(tested: bool | None) -> str:
    if tested is None:
        return "—"
    return "Yes" if tested else "No"


def load_qa_overrides() -> dict[str, dict[str, bool]]:
    """Optional overrides: { "app-name": { "standard": True, "ha": False } }."""
    path = ROOT / "qa-status.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def template_version(service: dict) -> str:
    dirname = service.get("dirname") or service["name"]
    path = SERVICES / dirname / "app.yaml"
    if not path.exists():
        return "—"
    try:
        import yaml

        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        image = (doc.get("spec") or {}).get("image") or {}
        tag = str(image.get("tag") or "").strip()
        repo = str(image.get("repository") or "").strip()
        if not tag and not repo:
            return "—"
        if tag:
            return tag
        return repo.split("/")[-1] if repo else "—"
    except Exception:
        return "—"


def icon_img(icon_url: str, name: str) -> str:
    url = (icon_url or "").strip()
    if not url:
        return ""
    alt = html.escape(name)
    safe_url = html.escape(url, quote=True)
    return (
        f'<img src="{safe_url}" width="32" height="32" alt="{alt}" '
        f'title="{alt}" style="vertical-align:middle;border-radius:4px;" />'
    )


def build_table(services: list[dict], overrides: dict) -> str:
    intro = [
        "## QA status",
        "",
        "Whether each catalog template has been validated by QA on a live Kubero",
        "cluster. **No** = not yet tested; **Yes** = QA verified; **—** = no HA",
        "variant in the catalog. **Version** is the Docker image tag from",
        "`services/<name>/app.yaml` (standard template). **Add-ons** lists Kubero",
        "operator add-ons (`displayName` in each template) — databases, caches, and",
        "queues are never embedded in the app container.",
        "",
        "To record a QA pass, edit `qa-status.json` and re-run",
        "`python scripts/generate-qa-table.py`:",
        "",
        "<!-- Markdown tables do not span the README width; HTML table below. -->",
        '<table width="100%">',
        "  <thead>",
        "    <tr>",
        '      <th align="left" width="40"></th>',
        '      <th align="left">App</th>',
        '      <th align="center" width="100">Version</th>',
        '      <th align="left">Add-ons</th>',
        '      <th align="center" width="90">Standard</th>',
        '      <th align="center" width="70">HA</th>',
        "    </tr>",
        "  </thead>",
        "  <tbody>",
    ]
    rows: list[str] = []
    for svc in sorted(services, key=lambda s: s["name"].lower()):
        name = svc["name"]
        o = overrides.get(name, {})
        std = qa_cell(o.get("standard", False))
        ha = qa_cell(o.get("ha") if "ha" in o else (False if ha_available(svc) else None))
        version = html.escape(template_version(svc))
        addons = html.escape(addons_cell(svc))
        icon = icon_img(svc.get("icon", ""), name)
        safe_name = html.escape(name)
        rows.append("    <tr>")
        rows.append(f"      <td>{icon}</td>")
        rows.append(f"      <td><strong>{safe_name}</strong></td>")
        rows.append(f'      <td align="center"><code>{version}</code></td>')
        rows.append(f"      <td>{addons}</td>")
        rows.append(f'      <td align="center">{std}</td>')
        rows.append(f'      <td align="center">{ha}</td>')
        rows.append("    </tr>")
    outro = [
        "  </tbody>",
        "</table>",
    ]
    return "\n".join(intro + rows + outro)


def main() -> None:
    services = json.loads(INDEX.read_text(encoding="utf-8"))["services"]
    overrides = load_qa_overrides()
    table = build_table(services, overrides)
    block = f"{MARKER_START}\n{table}\n{MARKER_END}"

    readme = README.read_text(encoding="utf-8")
    if MARKER_START not in readme:
        raise SystemExit(
            f"README missing {MARKER_START} markers — add them where the QA section should live."
        )
    before = readme.split(MARKER_START)[0].rstrip()
    after = readme.split(MARKER_END)[1].lstrip("\n") if MARKER_END in readme else ""
    README.write_text(before + "\n\n" + block + "\n\n" + after, encoding="utf-8")
    print(f"Updated QA table for {len(services)} apps in README.md")


if __name__ == "__main__":
    main()

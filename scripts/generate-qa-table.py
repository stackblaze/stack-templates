#!/usr/bin/env python3
"""Generate the QA status markdown table for README.md."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
INDEX = ROOT / "index.json"

MARKER_START = "<!-- qa-table:start -->"
MARKER_END = "<!-- qa-table:end -->"


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
    return json.loads(path.read_text(encoding="utf-8"))


def build_table(services: list[dict], overrides: dict) -> str:
    lines = [
        "## QA status",
        "",
        "Whether each catalog template has been validated by QA on a live Kubero",
        "cluster. **No** = not yet tested; **Yes** = QA verified; **—** = no HA",
        "variant in the catalog.",
        "",
        "To record a QA pass, edit `qa-status.json` and re-run",
        "`python scripts/generate-qa-table.py`:",
        "",
        "| App | Standard | HA |",
        "|-----|:--------:|:---:|",
    ]
    for svc in sorted(services, key=lambda s: s["name"].lower()):
        name = svc["name"]
        o = overrides.get(name, {})
        std = qa_cell(o.get("standard", False))
        ha = qa_cell(o.get("ha") if "ha" in o else (False if ha_available(svc) else None))
        lines.append(f"| {name} | {std} | {ha} |")
    return "\n".join(lines)


def main() -> None:
    services = json.loads(INDEX.read_text(encoding="utf-8"))["services"]
    overrides = load_qa_overrides()
    table = build_table(services, overrides)
    block = f"{MARKER_START}\n{table}\n{MARKER_END}"

    readme = README.read_text(encoding="utf-8")
    if MARKER_START in readme:
        before = readme.split(MARKER_START)[0].rstrip()
        after = readme.split(MARKER_END)[1].lstrip("\n") if MARKER_END in readme else ""
        README.write_text(before + "\n\n" + block + "\n\n" + after, encoding="utf-8")
    else:
        raise SystemExit(
            f"README missing {MARKER_START} markers — add them where the QA section should live."
        )
    print(f"Updated QA table for {len(services)} apps in README.md")


if __name__ == "__main__":
    main()

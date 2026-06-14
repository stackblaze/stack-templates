#!/usr/bin/env python3
"""Download icons for the 26 new templates from dashboard-icons CDN and patch refs."""
from __future__ import annotations
import json, re, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "services"
SPECS = Path(__file__).resolve().parent / "_specs"
BASE_RAW = "https://raw.githubusercontent.com/stackblaze/stack-templates/main/services"
CDN = "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png"
ICON_ANNOTATION = "kubero.dev/template.icon"

# slug -> dashboard-icons name (without .png). None = needs manual fallback.
SLUG_TO_ICON: dict[str, str] = {
    "ollama":         "ollama",
    "open-webui":     "open-webui",
    "litellm":        "litellm",
    "langfuse":       "langfuse",
    "localai":        "localai",
    "anythingllm":    "anythingllm",
    "authentik":      "authentik",
    "keycloak":       "keycloak",
    "zitadel":        "zitadel",
    "baserow":        "baserow",
    "teable":         "teable",
    "nocobase":       "nocobase",
    "pocketbase":     "pocketbase",
    "strapi":         "strapi",
    "clickhouse":     "clickhouse",
    "questdb":        "questdb",
    "timescaledb":    "timescale",
    "adminer":        "adminer",
    "pgadmin":        "pgadmin",
    "headscale":      "headscale",
    "listmonk":       "listmonk",
    "stalwart-mail":  "stalwart",
    "actual-budget":  "actual-budget",
    "firefly-iii":    "firefly-iii",
    "verdaccio":      "verdaccio",
    "seafile":        "seafile",
}


def download_icon(slug: str, icon_name: str) -> str | None:
    dest = SERVICES / slug / "icon.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    src_url = f"{CDN}/{icon_name}.png"
    try:
        req = urllib.request.Request(src_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read()
        if len(data) < 100:
            print(f"  WARN tiny file {slug} ({len(data)}b)")
            return None
        dest.write_bytes(data)
        return f"{BASE_RAW}/{slug}/icon.png"
    except Exception as exc:
        print(f"  FAIL {slug} <- {src_url}: {exc}")
        return None


def patch_yaml_icon(path: Path, new_url: str) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    pat = re.compile(r"(    " + re.escape(ICON_ANNOTATION) + r": ).*")
    new_text = pat.sub(lambda m: m.group(1) + new_url, text)
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False


def patch_spec_icon(slug: str, new_url: str) -> bool:
    p = SPECS / f"{slug}.json"
    if not p.exists():
        return False
    d = json.loads(p.read_text(encoding="utf-8"))
    d["icon"] = new_url
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def patch_index_icon(data: dict, slug: str, new_url: str) -> bool:
    for svc in data.get("services", []):
        if svc.get("name") == slug or svc.get("dirname") == slug:
            svc["icon"] = new_url
            return True
    return False


def main() -> int:
    index_path = ROOT / "index.json"
    index_data = json.loads(index_path.read_text(encoding="utf-8"))

    ok, failed = [], []
    for slug, icon_name in SLUG_TO_ICON.items():
        url = download_icon(slug, icon_name)
        if not url:
            failed.append(slug)
            continue
        patch_spec_icon(slug, url)
        patch_yaml_icon(SERVICES / slug / "app.yaml", url)
        patch_yaml_icon(SERVICES / slug / "app.ha.yaml", url)
        patch_index_icon(index_data, slug, url)
        ok.append(slug)
        print(f"  OK   {slug} <- {icon_name}.png")

    index_path.write_text(
        json.dumps(index_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"\nDone: {len(ok)} downloaded, {len(failed)} failed")
    if failed:
        print(f"  FAILED: {', '.join(failed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

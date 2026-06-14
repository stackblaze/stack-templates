#!/usr/bin/env python3
"""Fallback icons for the 6 apps missing from dashboard-icons."""
from __future__ import annotations
import json, re, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "services"
SPECS = Path(__file__).resolve().parent / "_specs"
BASE_RAW = "https://raw.githubusercontent.com/stackblaze/stack-templates/main/services"
ICON_ANNOTATION = "kubero.dev/template.icon"

DASH = "https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png"
SELF = "https://cdn.jsdelivr.net/gh/selfhst/icons/png"

# slug -> full source URL
SLUG_TO_URL: dict[str, str] = {
    "anythingllm":  f"{DASH}/anything-llm.png",
    "litellm":      f"{SELF}/litellm.png",
    "langfuse":     f"{SELF}/langfuse.png",
    "localai":      f"{SELF}/localai.png",
    "teable":       f"{SELF}/teable.png",
    "timescaledb":  "https://github.com/timescale.png",
}


def download(slug: str, src_url: str) -> str | None:
    dest = SERVICES / slug / "icon.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(src_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read()
        if len(data) < 100:
            print(f"  WARN tiny {slug}")
            return None
        dest.write_bytes(data)
        return f"{BASE_RAW}/{slug}/icon.png"
    except Exception as exc:
        print(f"  FAIL {slug} <- {src_url}: {exc}")
        return None


def patch_yaml(path: Path, url: str) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    pat = re.compile(r"(    " + re.escape(ICON_ANNOTATION) + r": ).*")
    text = pat.sub(lambda m: m.group(1) + url, text)
    path.write_text(text, encoding="utf-8")


def patch_spec(slug: str, url: str) -> None:
    p = SPECS / f"{slug}.json"
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        d["icon"] = url
        p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    index_path = ROOT / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))

    for slug, src in SLUG_TO_URL.items():
        url = download(slug, src)
        if not url:
            continue
        patch_spec(slug, url)
        patch_yaml(SERVICES / slug / "app.yaml", url)
        patch_yaml(SERVICES / slug / "app.ha.yaml", url)
        for svc in index["services"]:
            if svc.get("name") == slug or svc.get("dirname") == slug:
                svc["icon"] = url
        print(f"  OK   {slug} <- {src.split('/')[-1]}")

    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\nFallback icons done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

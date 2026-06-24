#!/usr/bin/env python3
"""
Discover screenshot URLs for templates missing them, optionally patch catalog files.

Discovery order:
  1. Website og:image / twitter:image
  2. Git host README images (GitHub, Codeberg, GitLab)

Usage:
  python3 scripts/scrape-template-screenshots.py              # dry-run + report
  python3 scripts/scrape-template-screenshots.py --apply      # write index.json + YAML
  python3 scripts/scrape-template-screenshots.py --slug foo   # single template
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ROOT / "services"
INDEX = ROOT / "index.json"
REPORT = ROOT / "scripts" / "screenshot-scrape-report.json"

SCREENSHOT_ANNOTATION = "kubero.dev/template.screenshots"
HEADERS = {"User-Agent": "Stackblaze-Templates-Bot/1.0"}
MIN_BYTES = 5000

BAD_SUBSTR = (
    "img.shields.io",
    "shields.io",
    "badge",
    "hitscounter",
    "githubassets.com",
    "avatars.githubusercontent",
    "avatar",
    "favicon",
    "logo.svg",
    "icon.svg",
    "/logo.",
    "apple-touch",
    "social-card",
    "opengraph.githubassets",
)

PREFERRED_KEYWORDS = (
    "screenshot",
    "preview",
    "demo",
    "banner",
    "hero",
    "docs/images",
    "/img/",
    "ui",
    "dashboard",
)


def fetch(url: str, timeout: int = 12) -> tuple[str, str]:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace"), resp.geturl()


def fetch_bytes(url: str, timeout: int = 15, max_bytes: int = 8192) -> tuple[bytes, str, str | None]:
    req = urllib.request.Request(
        url,
        headers={**HEADERS, "Range": f"bytes=0-{max_bytes - 1}"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        ct = resp.headers.get("Content-Type")
        cl = resp.headers.get("Content-Length")
        return data, resp.geturl(), ct


def normalize_url(u: str | None, base: str) -> str | None:
    if not u:
        return None
    u = u.strip().strip("\"'")
    if u.startswith("data:"):
        return None
    if u.startswith("//"):
        u = "https:" + u
    elif u.startswith("/"):
        u = urljoin(base, u)
    elif not u.startswith("http"):
        u = urljoin(base.rstrip("/") + "/", u)
    low = u.lower()
    if any(b in low for b in BAD_SUBSTR):
        return None
    return u


def og_image(html: str, base: str) -> str | None:
    patterns = [
        r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image',
        r'<meta[^>]+name=["\']twitter:image(?::src)?["\'][^>]+content=["\']([^"\']+)',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.I)
        if m:
            return normalize_url(m.group(1), base)
    return None


def git_readme_urls(source: str) -> list[tuple[str, str]]:
    """Return (branch, raw_readme_url) candidates."""
    source = source or ""
    m = re.match(r"https?://(?:www\.)?github\.com/([^/]+)/([^/]+)", source)
    if m:
        owner, repo = m.group(1), m.group(2).replace(".git", "")
        return [
            (b, f"https://raw.githubusercontent.com/{owner}/{repo}/{b}/README.md")
            for b in ("main", "master", "develop", "docs")
        ]
    m = re.match(r"https?://(?:www\.)?codeberg\.org/([^/]+)/([^/]+)", source)
    if m:
        owner, repo = m.group(1), m.group(2).replace(".git", "")
        return [
            (b, f"https://codeberg.org/{owner}/{repo}/raw/branch/{b}/README.md")
            for b in ("main", "master", "develop")
        ]
    m = re.match(r"https?://(?:www\.)?gitlab\.com/([^/]+)/([^/]+)", source)
    if m:
        owner, repo = m.group(1), m.group(2).replace(".git", "")
        return [
            (b, f"https://gitlab.com/{owner}/{repo}/-/raw/{b}/README.md")
            for b in ("main", "master", "develop")
        ]
    return []


def readme_image(source: str) -> str | None:
    for branch, readme_url in git_readme_urls(source):
        try:
            html, _ = fetch(readme_url, 8)
        except Exception:
            continue
        base = readme_url.rsplit("/", 1)[0] + "/"
        candidates: list[str] = []
        for im in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", html):
            u = normalize_url(im.split()[0], base)
            if u:
                candidates.append(u)
        for im in re.findall(r'<img[^>]+src=["\']([^"\']+)', html, re.I):
            u = normalize_url(im, base)
            if u:
                candidates.append(u)
        for u in candidates:
            low = u.lower()
            if any(k in low for k in PREFERRED_KEYWORDS):
                return u
        if candidates:
            return candidates[0]
    return None


def validate_image(url: str) -> tuple[bool, str | None]:
    try:
        data, final_url, ct = fetch_bytes(url)
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 405):
            try:
                data, final_url, ct = fetch_bytes(url.replace("HEAD", "GET"))
            except Exception as err:
                return False, str(err)
        else:
            return False, f"HTTP {exc.code}"
    except Exception as exc:
        return False, str(exc)

    if ct and "image" not in ct.lower():
        low = final_url.lower()
        if not any(low.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")):
            return False, f"not an image ({ct})"

    if len(data) < MIN_BYTES:
        return False, f"too small ({len(data)} bytes)"

    return True, None


def discover_screenshot(website: str, source: str) -> tuple[str | None, str | None]:
    site = (website or "").rstrip("/")
    if site:
        try:
            url = site if site.startswith("http") else "https://" + site
            html, final = fetch(url)
            img = og_image(html, final)
            if img:
                ok, _ = validate_image(img)
                if ok:
                    return img, "og"
        except Exception:
            pass

    img = readme_image(source)
    if img:
        ok, _ = validate_image(img)
        if ok:
            return img, "github"
    return None, None


def has_screenshot(svc: dict) -> bool:
    shots = svc.get("screenshots")
    if shots is None:
        return False
    if isinstance(shots, list):
        return any(isinstance(x, str) and x.strip() for x in shots)
    return False


def questionable(url: str, method: str) -> list[str]:
    flags: list[str] = []
    low = url.lower()
    if method == "og":
        flags.append("og_banner")
    if any(k in low for k in ("logo", "icon", "brand", "wordmark")):
        flags.append("logo_like")
    if method == "github" and not any(k in low for k in PREFERRED_KEYWORDS):
        flags.append("readme_unverified")
    return flags


def patch_yaml_screenshots(path: Path, urls: list[str]) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    payload = json.dumps(urls, ensure_ascii=False)
    pat = re.compile(r"(    " + re.escape(SCREENSHOT_ANNOTATION) + r": ).*")
    if pat.search(text):
        new_text = pat.sub(r"\g<1>'" + payload + "'", text)
    else:
        # Insert after template.icon if present, else after first annotation block line
        insert_pat = re.compile(r"(    kubero\.dev/template\.icon: .*\n)")
        if insert_pat.search(text):
            new_text = insert_pat.sub(
                r"\g<1>    " + SCREENSHOT_ANNOTATION + ": '" + payload + "'\n",
                text,
                count=1,
            )
        else:
            return False
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False


def patch_index_screenshots(data: dict, slug: str, urls: list[str]) -> bool:
    for svc in data.get("services", []):
        if svc.get("name") == slug or svc.get("dirname") == slug:
            svc["screenshots"] = urls
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write discovered URLs to index.json and app YAML files",
    )
    parser.add_argument("--slug", help="Process only this template dirname")
    args = parser.parse_args()

    index_data = json.loads(INDEX.read_text(encoding="utf-8"))
    services = [
        s
        for s in index_data.get("services", [])
        if not has_screenshot(s)
    ]
    if args.slug:
        services = [s for s in services if s.get("dirname") == args.slug]
        if not services:
            print(f"No missing-screenshot entry for slug {args.slug!r}", file=sys.stderr)
            return 1

    report: dict = {
        "applied": args.apply,
        "total_missing": len(services),
        "found": [],
        "missed": [],
        "questionable": [],
        "invalid_after_discovery": [],
    }

    stats = {"og": 0, "github": 0, "miss": 0, "invalid": 0}
    yaml_patched = 0
    index_patched = 0

    for svc in services:
        slug = svc.get("dirname") or svc.get("name") or "?"
        website = svc.get("website") or ""
        source = svc.get("source") or ""

        img, method = discover_screenshot(website, source)
        if not img:
            stats["miss"] += 1
            report["missed"].append({"slug": slug, "website": website, "source": source})
            print(f"MISS  {slug}")
            continue

        ok, err = validate_image(img)
        if not ok:
            stats["invalid"] += 1
            report["invalid_after_discovery"].append(
                {"slug": slug, "url": img, "method": method, "error": err}
            )
            print(f"BAD   {slug}: {err}")
            continue

        stats[method or "miss"] += 1
        flags = questionable(img, method or "")
        entry = {"slug": slug, "url": img, "method": method, "flags": flags}
        report["found"].append(entry)
        if flags:
            report["questionable"].append(entry)

        print(f"OK    [{method}] {slug}")

        if args.apply:
            urls = [img]
            svc_dir = SERVICES / slug
            for fname in ("app.yaml", "app.ha.yaml"):
                if patch_yaml_screenshots(svc_dir / fname, urls):
                    yaml_patched += 1
            if patch_index_screenshots(index_data, slug, urls):
                index_patched += 1

    if args.apply:
        INDEX.write_text(
            json.dumps(index_data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    report["stats"] = stats
    report["yaml_patched"] = yaml_patched
    report["index_patched"] = index_patched
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    found = stats["og"] + stats["github"]
    total = len(services)
    print()
    print(f"Templates without screenshots: {total}")
    print(f"Discovered + validated: {found} (og={stats['og']}, readme={stats['github']})")
    print(f"Missed: {stats['miss']}, invalid: {stats['invalid']}")
    if total:
        print(f"Success rate: {found / total * 100:.1f}%")
    print(f"Questionable picks: {len(report['questionable'])}")
    print(f"Report: {REPORT.relative_to(ROOT)}")
    if args.apply:
        print(f"Applied: index={index_patched}, yaml files={yaml_patched}")
    else:
        print("Dry run — pass --apply to update catalog files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

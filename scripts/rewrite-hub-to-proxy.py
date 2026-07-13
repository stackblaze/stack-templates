#!/usr/bin/env python3
"""Rewrite Docker Hub image refs to registry.stackblaze.cloud pull-through.

Only touches repository / image / imageName fields in app.yaml + app.ha.yaml.
Official images (no org/) get the library/ prefix required by Hub proxies.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

REG = "registry.stackblaze.cloud"
SKIP_PREFIXES = (
    "ghcr.io/",
    "quay.io/",
    "gcr.io/",
    "public.ecr.aws/",
    "lscr.io/",
    "mcr.microsoft.com/",
    "docker.redpanda.com/",
    "codeberg.org/",
    "registry.",
    "azurecr.io/",
    f"{REG}/",
)

FIELD = re.compile(
    r"^([ \t]*)(repository|image|imageName):\s*([^\s#]+)\s*(#.*)?$",
    re.M,
)


def is_hub(ref: str) -> bool:
    if ref.startswith("docker.io/"):
        return True
    if any(ref.startswith(p) for p in SKIP_PREFIXES):
        return False
    if re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/", ref):
        return False
    return bool(re.match(r"^[a-zA-Z0-9][a-zA-Z0-9._/-]*(:[a-zA-Z0-9._-]+)?$", ref))


def rewrite_ref(ref: str) -> str:
    if ref.startswith("docker.io/"):
        ref = ref[len("docker.io/") :]
    path = ref.split(":", 1)[0]
    if "/" not in path:
        # busybox:1.36 or repository: wordpress
        if ":" in ref:
            name, tag = ref.split(":", 1)
            return f"{REG}/library/{name}:{tag}"
        return f"{REG}/library/{ref}"
    return f"{REG}/{ref}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "services",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    changed_files: list[tuple[str, int]] = []
    examples: list[str] = []
    total = 0

    for path in sorted(args.root.rglob("app*.yaml")):
        if path.name not in ("app.yaml", "app.ha.yaml"):
            continue
        text = path.read_text(encoding="utf-8")
        subs = [0]

        def repl(m: re.Match[str]) -> str:
            indent, field, val, comment = (
                m.group(1),
                m.group(2),
                m.group(3),
                m.group(4) or "",
            )
            if not is_hub(val):
                return m.group(0)
            new = rewrite_ref(val)
            if new == val:
                return m.group(0)
            subs[0] += 1
            if len(examples) < 15:
                rel = path.relative_to(args.root.parent)
                examples.append(f"{rel}: {val} -> {new}")
            suffix = f" {comment}" if comment else ""
            return f"{indent}{field}: {new}{suffix}"

        new_text = FIELD.sub(repl, text)
        if not subs[0]:
            continue
        rel = str(path.relative_to(args.root.parent))
        changed_files.append((rel, subs[0]))
        total += subs[0]
        if not args.dry_run:
            path.write_text(new_text, encoding="utf-8", newline="\n")

    mode = "dry-run" if args.dry_run else "wrote"
    print(f"{mode}: files={len(changed_files)} substitutions={total}")
    print("--- examples ---")
    for e in examples:
        print(e)
    print("--- top files ---")
    for f, n in sorted(changed_files, key=lambda x: -x[1])[:20]:
        print(f"{n:3} {f}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
One-off Immich demo seeder — admin signup (if needed), album, sample photos.
Not wired into the template. Run against a live deployment:

  python3 scripts/seed-immich-demo.py \\
    --url https://your-immich.stackblaze.app \\
    --email demo@stackblaze.cloud --password '…' --name 'Demo Admin'

Credentials via flags or IMMICH_URL / IMMICH_EMAIL / IMMICH_PASSWORD / IMMICH_NAME.
Optional: --resolve HOST:IP for BunnyCDN bypass (curl --resolve style).
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Small royalty-free sample JPEGs (Unsplash source → local cache under /tmp).
SAMPLE_PHOTOS = [
    (
        "coastal-trail.jpg",
        "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1600&q=80",
    ),
    (
        "city-evening.jpg",
        "https://images.unsplash.com/photo-1514565131-fce0801e5785?w=1600&q=80",
    ),
    (
        "forest-path.jpg",
        "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=1600&q=80",
    ),
    (
        "mountain-lake.jpg",
        "https://images.unsplash.com/photo-1439066615861-d1af74d74000?w=1600&q=80",
    ),
    (
        "desert-dunes.jpg",
        "https://images.unsplash.com/photo-1509316785289-025f5b846b35?w=1600&q=80",
    ),
    (
        "northern-lights.jpg",
        "https://images.unsplash.com/photo-1483347756197-71ef80e95f73?w=1600&q=80",
    ),
    (
        "cafe-window.jpg",
        "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=1600&q=80",
    ),
    (
        "ocean-cliff.jpg",
        "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=1600&q=80",
    ),
]

ALBUM_NAME = "Stackblaze Demo"


def _ssl_ctx() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


class ImmichClient:
    def __init__(self, base: str, resolve: str | None = None):
        self.base = base.rstrip("/")
        self.token: str | None = None
        self.resolve = resolve  # "host:ip"
        self._opener = self._build_opener()

    def _build_opener(self):
        handlers: list = [urllib.request.HTTPSHandler(context=_ssl_ctx())]
        if self.resolve:
            host, ip = self.resolve.split(":", 1)
            # Force Host header; connect via IP using custom opener is awkward in
            # urllib — use curl for resolve path when provided.
            self._resolve_host = host
            self._resolve_ip = ip
        else:
            self._resolve_host = None
            self._resolve_ip = None
        return urllib.request.build_opener(*handlers)

    def request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        *,
        raw: bytes | None = None,
        content_type: str | None = None,
        auth: bool = True,
    ) -> tuple[int, object]:
        url = f"{self.base}{path}"
        data = raw
        headers: dict[str, str] = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        elif content_type and raw is not None:
            headers["Content-Type"] = content_type
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
            headers["x-immich-user-token"] = self.token
            headers["Cookie"] = f"immich_access_token={self.token}"

        if self._resolve_host:
            # Prefer curl for --resolve reliability through BunnyCDN.
            import subprocess
            import tempfile

            cmd = [
                "curl",
                "-sk",
                "--max-time",
                "120",
                "-X",
                method,
                "-w",
                "\n%{http_code}",
                "--resolve",
                f"{self._resolve_host}:443:{self._resolve_ip}",
            ]
            for k, v in headers.items():
                cmd += ["-H", f"{k}: {v}"]
            tmp = None
            if data is not None:
                tmp = tempfile.NamedTemporaryFile(delete=False)
                tmp.write(data)
                tmp.close()
                cmd += ["--data-binary", f"@{tmp.name}"]
            cmd.append(url)
            try:
                out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                out = e.output
            finally:
                if tmp is not None:
                    Path(tmp.name).unlink(missing_ok=True)
            text = out.decode("utf-8", errors="replace")
            if "\n" not in text:
                return 0, text
            body_text, code_s = text.rsplit("\n", 1)
            code = int(code_s.strip() or "0")
            if not body_text.strip():
                return code, None
            try:
                return code, json.loads(body_text)
            except json.JSONDecodeError:
                return code, body_text

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with self._opener.open(req, timeout=120) as resp:
                raw_body = resp.read()
                code = resp.status
        except urllib.error.HTTPError as e:
            raw_body = e.read()
            code = e.code
        if not raw_body:
            return code, None
        try:
            return code, json.loads(raw_body.decode())
        except json.JSONDecodeError:
            return code, raw_body.decode("utf-8", errors="replace")

    def upload_asset(self, path: Path, device_asset_id: str) -> tuple[int, object]:
        import subprocess
        import uuid

        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        boundary = f"----immich{uuid.uuid4().hex}"
        fields = {
            "deviceAssetId": device_asset_id,
            "deviceId": "stackblaze-demo-seed",
            "fileCreatedAt": now,
            "fileModifiedAt": now,
            "filename": path.name,
            "isFavorite": "false",
        }
        parts: list[bytes] = []
        for k, v in fields.items():
            parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
            )
        file_bytes = path.read_bytes()
        parts.append(
            (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="assetData"; filename="{path.name}"\r\n'
                f"Content-Type: image/jpeg\r\n\r\n"
            ).encode()
            + file_bytes
            + b"\r\n"
        )
        parts.append(f"--{boundary}--\r\n".encode())
        body = b"".join(parts)
        ctype = f"multipart/form-data; boundary={boundary}"

        if self._resolve_host:
            import tempfile

            tmp = tempfile.NamedTemporaryFile(delete=False)
            tmp.write(body)
            tmp.close()
            cmd = [
                "curl",
                "-sk",
                "--max-time",
                "180",
                "-X",
                "POST",
                "-w",
                "\n%{http_code}",
                "--resolve",
                f"{self._resolve_host}:443:{self._resolve_ip}",
                "-H",
                f"Content-Type: {ctype}",
                "-H",
                "Accept: application/json",
                "-H",
                f"Authorization: Bearer {self.token}",
                "-H",
                f"x-immich-user-token: {self.token}",
                "-H",
                f"Cookie: immich_access_token={self.token}",
                "--data-binary",
                f"@{tmp.name}",
                f"{self.base}/api/assets",
            ]
            try:
                out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                out = e.output
            finally:
                Path(tmp.name).unlink(missing_ok=True)
            text = out.decode("utf-8", errors="replace")
            body_text, code_s = text.rsplit("\n", 1)
            code = int(code_s.strip() or "0")
            try:
                return code, json.loads(body_text) if body_text.strip() else None
            except json.JSONDecodeError:
                return code, body_text

        return self.request(
            "POST",
            "/api/assets",
            raw=body,
            content_type=ctype,
        )


def download_samples(cache: Path) -> list[Path]:
    cache.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for name, url in SAMPLE_PHOTOS:
        dest = cache / name
        if dest.exists() and dest.stat().st_size > 10_000:
            paths.append(dest)
            continue
        print(f"download {name}")
        req = urllib.request.Request(url, headers={"User-Agent": "stackblaze-immich-seed/1"})
        with urllib.request.urlopen(req, timeout=60, context=_ssl_ctx()) as resp:
            dest.write_bytes(resp.read())
        paths.append(dest)
    return paths


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", default=os.environ.get("IMMICH_URL", ""))
    p.add_argument("--email", default=os.environ.get("IMMICH_EMAIL", ""))
    p.add_argument("--password", default=os.environ.get("IMMICH_PASSWORD", ""))
    p.add_argument("--name", default=os.environ.get("IMMICH_NAME", "Demo Admin"))
    p.add_argument(
        "--resolve",
        default=os.environ.get("IMMICH_RESOLVE", ""),
        help="host:ip for curl --resolve (BunnyCDN bypass)",
    )
    p.add_argument(
        "--meta",
        default="",
        help="JSON file with url/email/password/name_user fields",
    )
    p.add_argument("--cache", default="/tmp/immich-demo-photos")
    args = p.parse_args()

    if args.meta:
        meta = json.loads(Path(args.meta).read_text())
        args.url = args.url or meta.get("url") or f"https://{meta.get('host', '')}"
        args.email = args.email or meta.get("email", "")
        args.password = args.password or meta.get("password", "")
        args.name = args.name if args.name != "Demo Admin" else meta.get("name_user", args.name)

    if not args.url or not args.email or not args.password:
        print("Need --url/--email/--password (or --meta / env)", file=sys.stderr)
        return 2

    client = ImmichClient(args.url, resolve=args.resolve or None)

    code, cfg = client.request("GET", "/api/server/config", auth=False)
    print("config", code, cfg)
    if code != 200 or not isinstance(cfg, dict):
        print("server not reachable", file=sys.stderr)
        return 1

    if not cfg.get("isInitialized"):
        code, body = client.request(
            "POST",
            "/api/auth/admin-sign-up",
            {"email": args.email, "password": args.password, "name": args.name},
            auth=False,
        )
        print("admin-sign-up", code, body)
        if code not in (200, 201):
            return 1

    code, login = client.request(
        "POST",
        "/api/auth/login",
        {"email": args.email, "password": args.password},
        auth=False,
    )
    print("login", code, list(login.keys()) if isinstance(login, dict) else login)
    if code not in (200, 201) or not isinstance(login, dict) or not login.get("accessToken"):
        return 1
    client.token = login["accessToken"]
    Path("/tmp/immich-token.txt").write_text(client.token)

    # Album (idempotent by name)
    code, albums = client.request("GET", "/api/albums")
    album_id = None
    if isinstance(albums, list):
        for a in albums:
            if a.get("albumName") == ALBUM_NAME:
                album_id = a["id"]
                break
    if not album_id:
        code, album = client.request(
            "POST",
            "/api/albums",
            {"albumName": ALBUM_NAME, "description": "Seeded for Stackblaze catalog demo"},
        )
        print("create album", code, album)
        if code not in (200, 201) or not isinstance(album, dict):
            return 1
        album_id = album["id"]
    else:
        print("album exists", album_id)

    photos = download_samples(Path(args.cache))
    asset_ids: list[str] = []
    for i, photo in enumerate(photos):
        device_id = f"stackblaze-demo-{photo.name}"
        code, resp = client.upload_asset(photo, device_id)
        print(
            "upload",
            photo.name,
            code,
            resp if not isinstance(resp, dict) else resp.get("id") or resp.get("status"),
        )
        if code in (200, 201) and isinstance(resp, dict):
            aid = resp.get("id")
            if aid:
                asset_ids.append(aid)
        time.sleep(0.3)

    if asset_ids and album_id:
        code, body = client.request(
            "PUT",
            f"/api/albums/{album_id}/assets",
            {"ids": asset_ids},
        )
        # Fallback bulk endpoint shape used by newer Immich builds
        if code not in (200, 201):
            code, body = client.request(
                "PUT",
                "/api/albums/assets",
                {"albumIds": [album_id], "assetIds": asset_ids},
            )
        print("album add", code, body)

    print("done", {"album_id": album_id, "assets": len(asset_ids)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

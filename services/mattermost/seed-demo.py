#!/usr/bin/env python3
"""
Mattermost demo seeder — team, users, channels, posts, threads.
Runs on first boot when STACKBLAZE_LOAD_DEMO_DATA=true (see kubero-entrypoint.sh).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

MARKER = "stackblaze-demo-seed"

DEMO_USERS = [
    ("alex.morgan", "Alex", "Morgan", "alex.morgan@demo.stackblaze.app"),
    ("jordan.lee", "Jordan", "Lee", "jordan.lee@demo.stackblaze.app"),
    ("sam.patel", "Sam", "Patel", "sam.patel@demo.stackblaze.app"),
    ("taylor.brooks", "Taylor", "Brooks", "taylor.brooks@demo.stackblaze.app"),
    ("casey.nguyen", "Casey", "Nguyen", "casey.nguyen@demo.stackblaze.app"),
]

CHANNELS = [
    ("product-launch", "Product Launch", "Feature announcements and launch coordination"),
    ("engineering", "Engineering", "Deploys, incidents, and platform updates"),
    ("customer-success", "Customer Success", "Onboarding wins and customer feedback"),
    ("releases", "Releases", "Release notes and changelog discussion"),
]

MESSAGES: dict[str, list[tuple[str, str]]] = {
    "town-square": [
        ("admin", "Welcome to **Stackblaze Team** — our self-hosted Mattermost workspace for product, engineering, and customer updates."),
        ("alex.morgan", "Great to have everyone in one place. I'll post launch milestones in #product-launch."),
        ("jordan.lee", "Platform cluster is healthy — all template QA deploys passing."),
        ("sam.patel", "Attendize demo video and screenshots are live in the template catalog."),
        ("taylor.brooks", "Next up: Mattermost template polish — demo data + install modal video."),
        ("casey.nguyen", "Reminder: rotate default passwords on any public demo deployments."),
    ],
    "product-launch": [
        ("alex.morgan", "Shipped: Attendize 30s demo video (features → live UI screenshots)."),
        ("alex.morgan", "Template install modal now plays MP4 previews via jsDelivr."),
        ("jordan.lee", "Working on automated Playwright capture for ~200 app screenshots."),
        ("sam.patel", "Metabase and Tandoor already have real UI shots in the catalog."),
        ("taylor.brooks", "Goal this sprint: every validated template gets a real deployment screenshot."),
    ],
    "engineering": [
        ("jordan.lee", "`template-validation` QA pipeline deployed 12 apps overnight — 11 pass, 1 flaky ingress."),
        ("jordan.lee", "MariaDB + Valkey addons boot cleanly on `lite` storage class."),
        ("casey.nguyen", "kubectl exec timeouts on vm2 — using REST API + one-off Jobs as workaround."),
        ("sam.patel", "HyperFrames render loop: lint → validate → 1080p MP4 in ~45s locally."),
        ("admin", "Demo seeders run only when **Load demo data** is enabled at install."),
    ],
    "customer-success": [
        ("taylor.brooks", "New customer deployed Attendize on Stackblaze in under 4 minutes."),
        ("casey.nguyen", "They asked for a video in the install modal — now supported for MP4/WebM."),
        ("alex.morgan", "Adding per-app capture specs for login flows (Attendize, Mattermost, …)."),
        ("sam.patel", "Docs link: catalog refreshes every 10 min or via `refresh-catalog-cache`."),
    ],
    "releases": [
        ("admin", "**stack-templates** `main` — Attendize demo.mp4 replaced (30s, live UI)."),
        ("jordan.lee", "Added `scripts/capture-*.mjs` Playwright tooling @ 2× DPR."),
        ("alex.morgan", "Dashboard `BrowserMockup` plays video assets; skips broken slides."),
        ("taylor.brooks", "Next release: Mattermost + batch screenshot pipeline."),
    ],
    "off-topic": [
        ("sam.patel", "Coffee chat Friday 10:00 UTC — bring your favorite template requests."),
        ("casey.nguyen", "Anyone tried the new HyperFrames 30s app tour format?"),
    ],
}

THREAD_REPLIES = [
    ("jordan.lee", "Nice — the 2× DPR captures look sharp in the browser mockup."),
    ("alex.morgan", "+1, much better than the old 1024px manual grabs."),
    ("sam.patel", "I'll rerun batch capture once QA deploys finish."),
]


class MMClient:
    def __init__(self, base: str, token: str = ""):
        self.base = base.rstrip("/")
        self.token = token

    def request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        *,
        auth: bool = True,
    ) -> dict | list:
        data = None
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base}{path}", data=data, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{method} {path} -> {e.code}: {detail}") from e

    @classmethod
    def login(cls, base: str, login_id: str, password: str) -> MMClient:
        body = json.dumps({"login_id": login_id, "password": password}).encode("utf-8")
        req = urllib.request.Request(
            f"{base.rstrip('/')}/api/v4/users/login",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            token = resp.headers.get("Token") or resp.headers.get("token")
            if not token:
                raise RuntimeError("Login succeeded but no Token header returned")
            return cls(base, token.strip())


def bootstrap_admin(
    base: str,
    login: str,
    password: str,
    email: str,
) -> MMClient:
    try:
        return MMClient.login(base, login, password)
    except Exception:
        pass
    print(f"  creating first admin: {login}")
    MMClient(base).request(
        "POST",
        "/api/v4/users",
        {
            "username": login,
            "email": email,
            "password": password,
            "allow_marketing": False,
        },
        auth=False,
    )
    return MMClient.login(base, login, password)


def ensure_team(admin: MMClient, team_name: str, display_name: str) -> dict:
    try:
        team = admin.request("GET", f"/api/v4/teams/name/{team_name}")
        print(f"  team exists: {team['display_name']}")
        return team
    except RuntimeError as e:
        if "404" not in str(e):
            raise
    team = admin.request(
        "POST",
        "/api/v4/teams",
        {"name": team_name, "display_name": display_name, "type": "O"},
    )
    print(f"  created team: {display_name}")
    return team


def user_exists(client: MMClient, username: str) -> dict | None:
    try:
        return client.request("GET", f"/api/v4/users/username/{username}")
    except RuntimeError as e:
        if "404" in str(e):
            return None
        raise


def add_team_member(admin: MMClient, team_id: str, user_id: str) -> None:
    try:
        admin.request(
            "POST",
            f"/api/v4/teams/{team_id}/members",
            {"team_id": team_id, "user_id": user_id},
        )
    except RuntimeError as e:
        if "already" not in str(e).lower():
            raise


def add_user_to_channel(admin: MMClient, channel_id: str, user_id: str) -> None:
    try:
        admin.request(
            "POST",
            f"/api/v4/channels/{channel_id}/members",
            {"user_id": user_id},
        )
    except RuntimeError as e:
        err = str(e).lower()
        if "already" in err or "store.sql_channel.save_member" in err:
            return
        if "403" in err:
            return


def ensure_users(
    admin: MMClient,
    team_id: str,
    demo_password: str,
) -> tuple[dict[str, str], dict[str, str]]:
    tokens: dict[str, str] = {"admin": admin.token}
    user_ids: dict[str, str] = {}
    me = admin.request("GET", "/api/v4/users/me")
    user_ids["admin"] = me["id"]
    add_team_member(admin, team_id, me["id"])
    for username, first, last, email in DEMO_USERS:
        existing = user_exists(admin, username)
        if existing:
            print(f"  user exists: {username}")
            user_id = existing["id"]
        else:
            created = admin.request(
                "POST",
                "/api/v4/users",
                {
                    "username": username,
                    "email": email,
                    "password": demo_password,
                    "first_name": first,
                    "last_name": last,
                },
            )
            user_id = created["id"]
            print(f"  created user: {username}")
        add_team_member(admin, team_id, user_id)
        tokens[username] = MMClient.login(admin.base, username, demo_password).token
        user_ids[username] = user_id
    return tokens, user_ids


def ensure_channels(admin: MMClient, team_id: str) -> dict[str, str]:
    existing = {c["name"]: c for c in admin.request("GET", f"/api/v4/teams/{team_id}/channels")}
    ids: dict[str, str] = {}
    for name, display, purpose in CHANNELS:
        if name in existing:
            ids[name] = existing[name]["id"]
            print(f"  channel exists: #{name}")
            continue
        ch = admin.request(
            "POST",
            "/api/v4/channels",
            {
                "team_id": team_id,
                "name": name,
                "display_name": display,
                "purpose": purpose,
                "type": "O",
                "header": f"{MARKER} — demo channel",
            },
        )
        ids[name] = ch["id"]
        print(f"  created channel: #{name}")
    for name in ("town-square", "off-topic"):
        if name in existing:
            ids[name] = existing[name]["id"]
    return ids


def ensure_channel_members(
    admin: MMClient,
    channel_ids: dict[str, str],
    user_ids: list[str],
) -> None:
    for ch_id in channel_ids.values():
        for uid in user_ids:
            add_user_to_channel(admin, ch_id, uid)
            time.sleep(0.05)


def post_message(
    token: str,
    base: str,
    channel_id: str,
    message: str,
    root_id: str = "",
) -> str:
    client = MMClient(base, token)
    body: dict = {"channel_id": channel_id, "message": message}
    if root_id:
        body["root_id"] = root_id
    post = client.request("POST", "/api/v4/posts", body)
    return post["id"]


def channel_has_marker(admin: MMClient, channel_id: str) -> bool:
    posts = admin.request("GET", f"/api/v4/channels/{channel_id}/posts?per_page=30")
    order = posts.get("order", [])
    pmap = posts.get("posts", {})
    for pid in order:
        msg = pmap.get(pid, {}).get("message", "")
        if MARKER in msg or "Stackblaze Team" in msg:
            return True
    return False


def seed_channel(
    base: str,
    channel_id: str,
    channel_name: str,
    tokens: dict[str, str],
    admin: MMClient,
    admin_password: str,
    demo_password: str,
) -> None:
    if channel_has_marker(admin, channel_id):
        print(f"  skip #{channel_name} (demo content present)")
        return
    msgs = MESSAGES.get(channel_name, [])
    root_id = ""
    for i, (user, text) in enumerate(msgs):
        tagged = f"{text}\n\n_{MARKER}_"
        pw = admin_password if user == "admin" else demo_password
        if user not in tokens:
            tokens[user] = MMClient.login(base, user, pw).token
        root_id = post_message(
            tokens[user],
            base,
            channel_id,
            tagged,
            root_id if i == 0 else "",
        )
        time.sleep(0.12)
        if i == 0 and channel_name == "town-square":
            for reply_user, reply_text in THREAD_REPLIES:
                if reply_user not in tokens:
                    tokens[reply_user] = MMClient.login(base, reply_user, demo_password).token
                post_message(tokens[reply_user], base, channel_id, reply_text, root_id)
                time.sleep(0.08)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.environ.get("STACKBLAZE_APP_URL", "http://127.0.0.1:8065"))
    parser.add_argument("--login", default=os.environ.get("STACKBLAZE_DEMO_ADMIN_LOGIN", "admin"))
    parser.add_argument("--password", default=os.environ.get("STACKBLAZE_DEMO_ADMIN_PASSWORD", ""))
    parser.add_argument(
        "--demo-password",
        default=os.environ.get("STACKBLAZE_DEMO_USER_PASSWORD", "StackblazeDemo1!"),
    )
    parser.add_argument("--email", default=os.environ.get("STACKBLAZE_DEMO_ADMIN_EMAIL", "admin@localhost"))
    parser.add_argument("--team", default=os.environ.get("STACKBLAZE_DEMO_TEAM", "stackblaze-team"))
    parser.add_argument("--team-display", default=os.environ.get("STACKBLAZE_DEMO_TEAM_DISPLAY", "Stackblaze team"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.password:
        print("ERROR: admin password required (STACKBLAZE_DEMO_ADMIN_PASSWORD)", file=sys.stderr)
        return 1

    base = args.url.rstrip("/")
    print(f"Seeding Mattermost demo @ {base}")
    admin = bootstrap_admin(base, args.login, args.password, args.email)
    team = ensure_team(admin, args.team, args.team_display)
    team_id = team["id"]

    if args.dry_run:
        print("Dry run — would seed users, channels, and posts")
        return 0

    print("Users:")
    tokens, user_ids = ensure_users(admin, team_id, args.demo_password)
    print("Channels:")
    channel_ids = ensure_channels(admin, team_id)
    print("Channel membership (sidebar visibility):")
    ensure_channel_members(admin, channel_ids, list(user_ids.values()))
    print("Posts:")
    for ch_name, ch_id in channel_ids.items():
        seed_channel(
            base,
            ch_id,
            ch_name,
            tokens,
            admin,
            args.password,
            args.demo_password,
        )
        print(f"  seeded #{ch_name}")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

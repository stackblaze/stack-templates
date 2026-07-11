#!/usr/bin/env python3
"""Seed Uptime Kuma demo monitors + status page (requires uptime-kuma-api)."""
import argparse
from uptime_kuma_api import UptimeKumaApi, MonitorType

MONITORS = [
    dict(type=MonitorType.HTTP, name="Stackblaze API", url="https://api.stackblaze.cloud/api/templates/catalog", interval=60),
    dict(type=MonitorType.HTTP, name="Uptime Kuma GitHub", url="https://github.com/louislam/uptime-kuma", interval=60),
    dict(type=MonitorType.HTTP, name="Example.com", url="https://example.com", interval=60),
    dict(type=MonitorType.PING, name="Cloudflare DNS", hostname="1.1.1.1", interval=60),
    dict(type=MonitorType.HTTP, name="HTTP 503 probe", url="https://httpstat.us/503", interval=60),
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--user", default="admin")
    ap.add_argument("--password", default="changeme123")
    args = ap.parse_args()
    with UptimeKumaApi(args.url, timeout=30) as api:
        api.login(args.user, args.password)
        existing = {m.get("name") for m in (api.get_monitors() or [])}
        for m in MONITORS:
            if m["name"] in existing:
                print("skip", m["name"])
                continue
            print("add", m["name"], api.add_monitor(**m))
        mons = api.get_monitors() or []
        try:
            api.add_status_page("stackblaze", "Stackblaze Status")
        except Exception as e:
            print("status page may exist:", e)
        api.save_status_page(
            "stackblaze",
            title="Stackblaze Status",
            description="Demo public status page",
            theme="dark",
            published=True,
            showTags=False,
            domainNameList=[],
            footerText="Powered by Uptime Kuma on Stackblaze",
            customCSS="",
            googleAnalyticsId="",
            showPoweredBy=True,
            icon="/icon.svg",
            publicGroupList=[{
                "name": "Services",
                "weight": 1,
                "monitorList": [{"id": m["id"]} for m in mons[:4]],
            }],
        )
        print("status page saved")

if __name__ == "__main__":
    main()

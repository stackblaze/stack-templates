#!/bin/bash
# Populate Attendize demo orders, attendees, charts, and calendar events.
# Run inside the Attendize *web* pod (not the worker):
#
#   bash /path/to/seed-demo-analytics.sh
#
# Or manually:
#   cd /usr/share/nginx/html
#   wget -q -O database/seeds/DemoAnalyticsSeeder.php \
#     https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/attendize/DemoAnalyticsSeeder.php
#   composer dump-autoload --no-interaction --quiet
#   php artisan db:seed --class=DemoAnalyticsSeeder --force

set -euo pipefail

APP_ROOT="${APP_ROOT:-/usr/share/nginx/html}"
BASE="${STACKBLAZE_BOOTSTRAP_BASE:-https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/attendize}"

cd "${APP_ROOT}"

echo "[attendize-demo] Fetching DemoAnalyticsSeeder.php"
wget -q -O database/seeds/DemoAnalyticsSeeder.php "${BASE}/DemoAnalyticsSeeder.php"

composer dump-autoload --no-interaction --quiet --working-dir="${APP_ROOT}" || true

echo "[attendize-demo] Seeding demo analytics"
php artisan db:seed --class=DemoAnalyticsSeeder --force

echo "[attendize-demo] Done — refresh the organiser dashboard and event pages"

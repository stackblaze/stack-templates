#!/bin/sh
# Turns upstream's excalidraw.com build into a self-contained one.
# Run from the root of an excalidraw checkout. Fails loudly if upstream moved
# the code this relies on, so a version bump cannot silently ship a broken app.
set -eu
here=$(dirname "$0")

# 1. Rooms, room images and share-link images: this instance's own storage
#    API instead of excalidraw.com's Firebase project (same exports).
test -f excalidraw-app/data/firebase.ts
cp "$here/storage.ts" excalidraw-app/data/firebase.ts

# 2. Backends on this instance's own origin.
env=.env.production
test -f "$env"
set_env() {
  grep -q "^$1=" "$env" || { echo "missing $1 in $env"; exit 1; }
  sed -i "s#^$1=.*#$1=$2#" "$env"
}
set_env VITE_APP_WS_SERVER_URL /
set_env VITE_APP_BACKEND_V2_GET_URL /api/v2/scenes/
set_env VITE_APP_BACKEND_V2_POST_URL /api/v2/scenes
set_env VITE_APP_ENABLE_TRACKING false
# Firebase is no longer used; the config is single-quoted JSON on one line.
sed -i "s#^VITE_APP_FIREBASE_CONFIG=.*#VITE_APP_FIREBASE_CONFIG='{}'#" "$env"

# 3. No third-party analytics script and no redirect to excalidraw.com's
#    paid app in index.html.
html=excalidraw-app/index.html
grep -q 'simpleanalyticscdn.com' "$html"
grep -q 'excplus-autoredirect' "$html"
node - "$html" <<'NODE'
const fs = require("fs");
const file = process.argv[2];
let s = fs.readFileSync(file, "utf8");
const cut = (start, end) => {
  const a = s.indexOf(start);
  const b = s.indexOf(end, a);
  if (a < 0 || b < 0) throw new Error(`block not found: ${start}`);
  s = s.slice(0, a) + s.slice(b + end.length);
};
cut("<!-- 100% privacy friendly analytics -->", "<!-- end LEGACY GOOGLE ANALYTICS -->");
cut("<script>\n      // Redirect Excalidraw+ users", "</script>");
if (/simpleanalytics|excplus-autoredirect/.test(s)) throw new Error("patch incomplete");
fs.writeFileSync(file, s);
NODE

echo "patches applied"

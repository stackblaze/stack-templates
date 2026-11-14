#!/bin/sh
# StackBlaze: wait for the database, apply pending migrations, then start Next.js.
set -e
node scripts/wait-for-db.mjs
node node_modules/payload/bin.js migrate
exec "$@"

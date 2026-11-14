#!/bin/sh
set -e
node /opt/app/scripts/wait-for-db.js
exec "$@"

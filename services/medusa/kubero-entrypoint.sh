#!/bin/sh
set -eu

cd /server

echo "Running Medusa database migrations..."
npx medusa db:migrate

if [ -n "${MEDUSA_ADMIN_EMAIL:-}" ] && [ -n "${MEDUSA_ADMIN_PASSWORD:-}" ]; then
  echo "Ensuring admin user ${MEDUSA_ADMIN_EMAIL} exists..."
  npx medusa user -e "$MEDUSA_ADMIN_EMAIL" -p "$MEDUSA_ADMIN_PASSWORD" || true
fi

exec npx medusa start

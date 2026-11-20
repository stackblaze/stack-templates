#!/bin/sh
# StackBlaze start for Medusa: wait for Postgres (a real login) and Valkey,
# run upstream's predeploy step (migrations, link sync and migration scripts,
# which on a new database include the starter's store seed and the first
# admin user), then start the server.
set -eu
cd /server

node /usr/local/lib/stackblaze/wait-for-services.js

echo "[stackblaze] running database migrations"
./node_modules/.bin/medusa db:migrate

echo "[stackblaze] starting Medusa"
exec ./node_modules/.bin/medusa start

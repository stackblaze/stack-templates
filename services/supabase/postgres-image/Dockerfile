# CloudNativePG's PostgreSQL 16 image plus wal2json, which Supabase Realtime's
# Postgres Changes use to decode the WAL (the stock image doesn't ship it).
# Built by .github/workflows/build-supabase-postgres.yaml as
# ghcr.io/stackblaze/stack-templates/supabase-postgres.
# The digest is ghcr.io/cloudnative-pg/postgresql:16 (16.15, bullseye) on 2026-11-14.
FROM ghcr.io/cloudnative-pg/postgresql:16@sha256:34cd4159d07b3410a1b29da35072e2e927a0905e717a61afa3814624a2e8859a
USER root
# PGDG moved bullseye to its archive host.
RUN sed -i 's|apt.postgresql.org/pub/repos/apt|apt-archive.postgresql.org/pub/repos/apt|' /etc/apt/sources.list.d/*.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends postgresql-16-wal2json \
 && rm -rf /var/lib/apt/lists/* \
 && test -f /usr/lib/postgresql/16/lib/wal2json.so
USER 26

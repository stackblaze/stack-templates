# Medusa publishes no runtime image: a Medusa store is a project you build.
# This image is upstream's official starter (medusajs/dtc-starter, backend
# app only) at a pinned commit, built the way upstream's deployment guide
# says (`medusa build`, then `npm install` in .medusa/server), with a
# StackBlaze medusa-config.ts (Valkey modules, local files on the volume) and
# one extra migration script that creates the first admin user.
ARG NODE_IMAGE=docker.io/library/node:22.23.5-bookworm-slim

FROM ${NODE_IMAGE} AS builder

# medusajs/dtc-starter "chore: update @medusajs/* to v2.22.7 (#103)"
ARG STARTER_SHA=44f2979627d8b9dac3336ee039a99a433f4c3123

RUN apt-get update \
  && apt-get install -y --no-install-recommends git python3 make g++ ca-certificates \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /src
RUN git init -q . \
  && git remote add origin https://github.com/medusajs/dtc-starter.git \
  && git fetch -q --depth 1 origin "$STARTER_SHA" \
  && git checkout -q FETCH_HEAD

COPY medusa-config.ts apps/backend/medusa-config.ts
COPY src/migration-scripts/stackblaze-admin.ts apps/backend/src/migration-scripts/stackblaze-admin.ts

ENV MEDUSA_DISABLE_TELEMETRY=true
RUN corepack enable \
  && corepack prepare pnpm@10.11.1 --activate \
  && pnpm install --frozen-lockfile --filter @dtc/backend... \
  && pnpm --filter @dtc/backend build

WORKDIR /src/apps/backend/.medusa/server
RUN npm install --omit=dev --no-audit --no-fund \
  && npm cache clean --force

FROM ${NODE_IMAGE}

RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates tini \
  && rm -rf /var/lib/apt/lists/* \
  && mkdir -p /server/static \
  && chown -R node:node /server

WORKDIR /server
COPY --from=builder --chown=node:node /src/apps/backend/.medusa/server /server
COPY --chown=node:node wait-for-services.js /usr/local/lib/stackblaze/wait-for-services.js
COPY --chown=node:node docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

USER node
ENV NODE_ENV=production \
    PORT=9000 \
    MEDUSA_DISABLE_TELEMETRY=true
EXPOSE 9000
VOLUME ["/server/static"]
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/docker-entrypoint.sh"]

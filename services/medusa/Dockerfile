# Medusa does not publish an official production image. This builds the
# official DTC starter backend (Medusa 2.21) for the catalog template.
FROM node:22-bookworm-slim AS builder

RUN apt-get update \
  && apt-get install -y --no-install-recommends git python3 make g++ ca-certificates \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /src
RUN git clone --depth 1 https://github.com/medusajs/dtc-starter.git .
COPY medusa-config.ts apps/backend/medusa-config.ts

RUN corepack enable \
  && corepack prepare pnpm@10.11.1 --activate \
  && pnpm install --frozen-lockfile --filter @dtc/backend... \
  && pnpm --filter @dtc/backend build

WORKDIR /src/apps/backend/.medusa/server
RUN npm install --omit=dev

FROM node:22-bookworm-slim

RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates \
  && rm -rf /var/lib/apt/lists/* \
  && mkdir -p /server/static \
  && chown -R node:node /server

WORKDIR /server
COPY --from=builder --chown=node:node /src/apps/backend/.medusa/server /server
COPY --chown=node:node kubero-entrypoint.sh /usr/local/bin/kubero-entrypoint.sh
RUN chmod +x /usr/local/bin/kubero-entrypoint.sh

USER node
ENV NODE_ENV=production
ENV PORT=9000
EXPOSE 9000
ENTRYPOINT ["/usr/local/bin/kubero-entrypoint.sh"]

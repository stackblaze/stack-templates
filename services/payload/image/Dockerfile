# Payload publishes no runtime image: a Payload app is a Next.js project you build.
# This is `create-payload-app@3.93.0 -t website --db postgres` (Payload's website
# starter: pages, posts, media, categories, forms, search, redirects, SEO) with
# the changes marked "StackBlaze:" in the source. To change collections or config,
# edit this project, run `npm run payload migrate:create` against a database, and
# rebuild the image; migrations run on every start (docker-entrypoint.sh).
#
# Build-time trap: nothing here reads the database or the public URL at build
# time. Never pass NEXT_PUBLIC_SERVER_URL as a build arg: Next.js would inline it.
FROM node:24.22.3-trixie-slim AS build

WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
COPY package.json package-lock.json .npmrc ./
RUN npm ci --include=dev --no-audit --no-fund
COPY . .
RUN npm run build && rm -rf .next/cache && npm prune --omit=dev && npm cache clean --force

FROM node:24.22.3-trixie-slim

RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates tini \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=build --chown=node:node /app /app
RUN mkdir -p /app/public/media /app/.next/cache && chown -R node:node /app/public /app/.next/cache

USER node
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
EXPOSE 3000
ENTRYPOINT ["/usr/bin/tini", "--", "/app/docker-entrypoint.sh"]
CMD ["sh", "-c", "exec node_modules/.bin/next start -H 0.0.0.0 -p ${PORT}"]

# Strapi publishes no runtime image: a Strapi app is a project you build.
# This is `create-strapi-app@5.62.0 --ts --example` (the example blog model:
# Article, Author, Category, About, Global) with PostgreSQL, the SMTP email
# provider and the admin panel built in. Build your own content types from
# this directory: `npm ci && npm run develop`, then rebuild the image.
FROM node:24.22.3-trixie-slim AS build

RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 make g++ ca-certificates \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/app
ENV NODE_ENV=production STRAPI_TELEMETRY_DISABLED=true
COPY package.json package-lock.json ./
RUN npm ci --include=dev --no-audit --no-fund
COPY . .
RUN npm run build && npm prune --omit=dev && npm cache clean --force

FROM node:24.22.3-trixie-slim

RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates tini \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/app
COPY --from=build --chown=node:node /opt/app /opt/app
RUN mkdir -p /opt/app/public/uploads /opt/app/.tmp && chown -R node:node /opt/app/public /opt/app/.tmp

USER node
ENV NODE_ENV=production \
    HOST=0.0.0.0 \
    PORT=1337 \
    STRAPI_TELEMETRY_DISABLED=true \
    STRAPI_DISABLE_UPDATE_NOTIFICATION=true
EXPOSE 1337
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/opt/app/node_modules/.bin/strapi", "start"]

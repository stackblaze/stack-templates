# StackBlaze build of Excalidraw (https://github.com/excalidraw/excalidraw, MIT).
#
# Upstream publishes only excalidraw/excalidraw:latest, a build of excalidraw.com
# whose live collaboration, shareable links and room images talk to
# excalidraw.com's own servers, which refuse other origins. This image builds
# the same app at a pinned commit, points those features at this instance
# (patches/), drops the third-party analytics script, and serves everything
# from one Node process running as uid 1000 (server/server.mjs).

# Upstream commit: the head of excalidraw's `release` branch (what
# excalidraw/excalidraw:latest is built from) on 2026-11-12.
ARG EXCALIDRAW_COMMIT=1440f2d2f84af0d5e19df4d94653200a6064f1ed

FROM node:24.22.1-bookworm@sha256:d862bb5d082c5ae0210ac07e8c0344cb8cf7bef6d78e9b8c50c179da923108ea AS app
ARG EXCALIDRAW_COMMIT
WORKDIR /src
RUN git init -q . \
 && git remote add origin https://github.com/excalidraw/excalidraw.git \
 && git fetch -q --depth 1 origin "$EXCALIDRAW_COMMIT" \
 && git checkout -q FETCH_HEAD
COPY patches /patches
RUN sh /patches/apply.sh
RUN npx -y yarn@1.22.22 --frozen-lockfile --network-timeout 600000
ENV NODE_ENV=production
RUN npx -y yarn@1.22.22 build:app:docker \
 && cd excalidraw-app/build \
 && rm -f *.map \
 && find . -type f \( -name '*.js' -o -name '*.css' -o -name '*.html' -o -name '*.json' -o -name '*.svg' -o -name '*.webmanifest' -o -name '*.txt' \) -size +1k -exec gzip -k -9 {} +

FROM node:24.22.1-alpine@sha256:06d7adf3e0ef61a13f1d28682726366f97a15aa1888c934d3ecec86c33918b53
ARG EXCALIDRAW_COMMIT
LABEL org.opencontainers.image.revision.excalidraw=$EXCALIDRAW_COMMIT
WORKDIR /app
COPY server/package.json server/package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts && npm cache clean --force
COPY server/server.mjs ./
COPY --from=app /src/excalidraw-app/build /app/public
RUN mkdir -p /data && chown node:node /data
ENV NODE_ENV=production PORT=8080 PUBLIC_DIR=/app/public DATA_DIR=/data
USER node
EXPOSE 8080
VOLUME /data
CMD ["node", "server.mjs"]

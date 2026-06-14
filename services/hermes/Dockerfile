# Multi-stage build of hashicorp-forge/hermes v0.5.0 for ghcr.io/stackblaze/stack-templates/hermes.
# Upstream ships a Dockerfile that expects a pre-built binary; this builds from source.

ARG HERMES_VERSION=v0.5.0

FROM node:20-bookworm AS web
ARG HERMES_VERSION
WORKDIR /src
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 --branch ${HERMES_VERSION} https://github.com/hashicorp-forge/hermes.git .
WORKDIR /src/web
RUN corepack enable && yarn install && rm -rf dist/ && yarn build

FROM golang:1.22-bookworm AS gobuild
ARG HERMES_VERSION
WORKDIR /src
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 --branch ${HERMES_VERSION} https://github.com/hashicorp-forge/hermes.git .
COPY --from=web /src/web/dist ./web/dist
ENV CGO_ENABLED=0
RUN go build -o ./hermes ./cmd/hermes

FROM alpine:3.21.5
WORKDIR /app
RUN apk --no-cache add ca-certificates
COPY --from=gobuild /src/hermes /app/hermes
COPY --from=gobuild /src/configs /app/configs
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh
EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["server"]

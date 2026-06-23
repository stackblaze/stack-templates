# Build hashicorp-forge/hermes v0.5.0 — mirrors upstream CI (Node 16 + Go 1.18+).
ARG HERMES_VERSION=v0.5.0

FROM golang:1.22-bookworm AS build
ARG HERMES_VERSION
WORKDIR /src
RUN apt-get update && apt-get install -y git curl ca-certificates && \
    curl -fsSL https://deb.nodesource.com/setup_16.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 --branch ${HERMES_VERSION} https://github.com/hashicorp-forge/hermes.git .
RUN corepack enable
ENV SKIP_YARN_COREPACK_CHECK=true \
    YARN_IGNORE_NODE=1 \
    CGO_ENABLED=0 \
    GOOS=linux \
    GOARCH=amd64
# v0.5.0 has no Word add-in embed; newer refs need `make build/linux` instead.
RUN make web/set-yarn-version && make web/build && make bin/linux

FROM alpine:3.21.5
WORKDIR /app
RUN apk --no-cache add ca-certificates
COPY --from=build /src/hermes /app/hermes
COPY --from=build /src/configs /app/configs
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh
EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["server"]

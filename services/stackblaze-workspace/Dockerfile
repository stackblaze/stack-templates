# Stackblaze Workspace workspace — code-server + Node toolchain for in-browser dev.
# Published as ghcr.io/stackblaze/stackblaze-workspace (build in CI from this directory).
FROM ghcr.io/coder/code-server:4.104.3

USER root

RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    ripgrep \
  && rm -rf /var/lib/apt/lists/* \
  && curl -fsSL https://get.pnpm.io/install.sh | env PNPM_VERSION=9.15.4 sh - \
  && ln -sf /root/.local/share/pnpm/pnpm /usr/local/bin/pnpm \
  && ln -sf /root/.local/share/pnpm/node /usr/local/bin/node 2>/dev/null || true

# Default project dir (PVC mount target in app.yaml).
RUN mkdir -p /home/coder/project \
  && chown -R coder:coder /home/coder/project

USER coder
WORKDIR /home/coder/project

# code-server listens on $PORT (8080 in Kubero web spec).
ENV PORT=8080

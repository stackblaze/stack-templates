#!/bin/sh
# n8n bootstrap: start n8n, optionally seed Stackblaze demo workflows.
set -eu

STACKBLAZE_BOOTSTRAP_BASE="${STACKBLAZE_BOOTSTRAP_BASE:-https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/n8n}"
N8N_PORT="${N8N_PORT:-5678}"
N8N_URL="http://127.0.0.1:${N8N_PORT}"
SEED_MARKER_FILE="${SEED_MARKER_FILE:-/home/node/.n8n/.stackblaze-demo-seeded}"
DEMO_EMAIL="${STACKBLAZE_DEMO_EMAIL:-demo@stackblaze.local}"
DEMO_PASSWORD="${STACKBLAZE_DEMO_PASSWORD:-changeme}"
DEMO_FIRST="${STACKBLAZE_DEMO_FIRST_NAME:-Demo}"
DEMO_LAST="${STACKBLAZE_DEMO_LAST_NAME:-User}"

log() {
  echo "[n8n-bootstrap] $*"
}

wait_for_api() {
  log "Waiting for n8n on ${N8N_URL}"
  i=0
  while [ "$i" -lt 180 ]; do
    if node -e "fetch(process.argv[1]).then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))" \
      "${N8N_URL}/healthz" 2>/dev/null; then
      log "n8n API is up"
      return 0
    fi
    if node -e "fetch(process.argv[1]).then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))" \
      "${N8N_URL}/rest/settings" 2>/dev/null; then
      log "n8n API is up"
      return 0
    fi
    i=$((i + 1))
    sleep 2
  done
  log "ERROR: n8n not reachable after 6 minutes"
  return 1
}

fetch_seed() {
  dest="$1"
  if command -v wget >/dev/null 2>&1; then
    wget -q -O "${dest}" "${STACKBLAZE_BOOTSTRAP_BASE}/seed-demo.mjs" && return 0
  fi
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL -o "${dest}" "${STACKBLAZE_BOOTSTRAP_BASE}/seed-demo.mjs" && return 0
  fi
  # Node fetch fallback (n8n image always has node)
  node -e "
    const fs = require('fs');
    fetch(process.argv[1]).then(async (r) => {
      if (!r.ok) process.exit(1);
      fs.writeFileSync(process.argv[2], await r.text());
    }).catch(() => process.exit(1));
  " "${STACKBLAZE_BOOTSTRAP_BASE}/seed-demo.mjs" "${dest}"
}

run_demo_seed() {
  if [ "${STACKBLAZE_LOAD_DEMO_DATA:-false}" != "true" ]; then
    log "STACKBLAZE_LOAD_DEMO_DATA disabled — skipping demo seed"
    return 0
  fi

  if [ -f "${SEED_MARKER_FILE}" ]; then
    log "Demo seed marker present — skipping"
    return 0
  fi

  wait_for_api || return 1

  seed_js="/tmp/seed-demo.mjs"
  if ! fetch_seed "${seed_js}"; then
    log "ERROR: could not download seed-demo.mjs from ${STACKBLAZE_BOOTSTRAP_BASE}"
    return 1
  fi

  export STACKBLAZE_APP_URL="${N8N_URL}"
  export STACKBLAZE_DEMO_EMAIL="${DEMO_EMAIL}"
  export STACKBLAZE_DEMO_PASSWORD="${DEMO_PASSWORD}"
  export STACKBLAZE_DEMO_FIRST_NAME="${DEMO_FIRST}"
  export STACKBLAZE_DEMO_LAST_NAME="${DEMO_LAST}"

  if ! node "${seed_js}"; then
    log "ERROR: demo seed failed"
    return 1
  fi

  mkdir -p "$(dirname "${SEED_MARKER_FILE}")"
  touch "${SEED_MARKER_FILE}"
  log "Demo seed complete (owner ${DEMO_EMAIL} / ${DEMO_PASSWORD})"
}

# Start n8n (same as image docker-entrypoint.sh with no args)
if [ -x /docker-entrypoint.sh ]; then
  /docker-entrypoint.sh &
else
  n8n &
fi
N8N_PID=$!

trap 'kill -TERM "${N8N_PID}" 2>/dev/null || true' TERM INT

(
  sleep 5
  run_demo_seed || log "Demo seed failed (n8n will still run)"
) &

wait "${N8N_PID}"

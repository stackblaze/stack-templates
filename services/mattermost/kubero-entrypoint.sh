#!/bin/bash
set -euo pipefail

STACKBLAZE_BOOTSTRAP_BASE="${STACKBLAZE_BOOTSTRAP_BASE:-https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/mattermost}"
MM_PORT="${MM_PORT:-8065}"
MM_URL="http://127.0.0.1:${MM_PORT}"
SEED_MARKER_FILE="/mattermost/data/.stackblaze-demo-seeded"

log() {
  echo "[mattermost-bootstrap] $*"
}

wait_for_api() {
  log "Waiting for Mattermost API on ${MM_URL}"
  for _ in $(seq 1 180); do
    if curl -sf "${MM_URL}/api/v4/system/ping" >/dev/null 2>&1; then
      log "Mattermost API is up"
      return 0
    fi
    sleep 2
  done
  log "ERROR: Mattermost API not reachable after 6 minutes"
  return 1
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

  wait_for_api

  local seed_py="/tmp/seed-demo.py"
  if ! wget -q -O "${seed_py}" "${STACKBLAZE_BOOTSTRAP_BASE}/seed-demo.py" 2>/dev/null; then
    if ! curl -fsSL -o "${seed_py}" "${STACKBLAZE_BOOTSTRAP_BASE}/seed-demo.py" 2>/dev/null; then
      log "ERROR: could not download seed-demo.py from ${STACKBLAZE_BOOTSTRAP_BASE}"
      return 1
    fi
  fi

  export STACKBLAZE_APP_URL="${MM_URL}"
  export STACKBLAZE_DEMO_ADMIN_LOGIN="${STACKBLAZE_DEMO_ADMIN_LOGIN:-admin}"
  export STACKBLAZE_DEMO_ADMIN_PASSWORD="${STACKBLAZE_DEMO_ADMIN_PASSWORD:-changeme}"
  export STACKBLAZE_DEMO_ADMIN_EMAIL="${STACKBLAZE_DEMO_ADMIN_EMAIL:-admin@localhost}"
  export STACKBLAZE_DEMO_USER_PASSWORD="${STACKBLAZE_DEMO_USER_PASSWORD:-StackblazeDemo1!}"
  export STACKBLAZE_DEMO_TEAM="${STACKBLAZE_DEMO_TEAM:-stackblaze-team}"
  export STACKBLAZE_DEMO_TEAM_DISPLAY="${STACKBLAZE_DEMO_TEAM_DISPLAY:-Stackblaze team}"

  if command -v python3 >/dev/null 2>&1; then
    python3 "${seed_py}" --url "${MM_URL}"
  elif command -v python >/dev/null 2>&1; then
    python "${seed_py}" --url "${MM_URL}"
  else
    log "ERROR: python not found in Mattermost image — cannot seed demo data"
    return 1
  fi

  touch "${SEED_MARKER_FILE}"
  log "Demo seed complete"
}

# Start Mattermost in the background, seed when enabled, then wait on the server.
docker-entrypoint.sh mattermost &
MM_PID=$!

trap 'kill -TERM "${MM_PID}" 2>/dev/null || true' TERM INT

(
  sleep 5
  run_demo_seed || log "Demo seed failed (Mattermost will still run)"
) &

wait "${MM_PID}"

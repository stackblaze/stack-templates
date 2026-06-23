#!/usr/bin/env bash
# Queue smoke tests for DB-migrated templates via the platform QA API.
#
# Prerequisites:
#   1. Push stack-templates changes to the branch the catalog uses (main).
#   2. Super-admin JWT or platform API token in STACKBLAZE_TOKEN.
#   3. QA target cluster set in Platform → Templates (e.g. shared-east-1).
#
# Usage:
#   export STACKBLAZE_TOKEN='…'   # from dash → Platform → Tokens, or session JWT
#   export STACKBLAZE_API='https://api.stackblaze.cloud'  # optional
#   ./scripts/qa-validate-migrated.sh
#
# Options:
#   --refresh-cache   POST refresh-catalog-cache before validating
#   --dry-run         print curl commands only

set -euo pipefail

API="${STACKBLAZE_API:-https://api.stackblaze.cloud}"
DRY_RUN=0
REFRESH=0

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --refresh-cache) REFRESH=1 ;;
    *) echo "Unknown option: $arg" >&2; exit 1 ;;
  esac
done

if [[ -z "${STACKBLAZE_TOKEN:-}" ]]; then
  echo "Set STACKBLAZE_TOKEN to a super-admin JWT or platform API token." >&2
  exit 1
fi

AUTH=(-H "Authorization: Bearer ${STACKBLAZE_TOKEN}" -H "Content-Type: application/json")

NAMES=(
  wikijs directus doccano lychee focalboard headscale openobserve shlink
  gitea forgejo fief nocodb linkding wallabag kanboard vaultwarden uptime-kuma
  memos erugo gotify anythingllm countly
  homarr homebox twofauth flowise docuseal shiori opengist
)

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf 'curl -sS -X %s %q %s\n' "$1" "${API}${2}" "${*:3}"
  else
    curl -sS -X "$1" "${API}${2}" "${AUTH[@]}" "${@:3}"
  fi
}

if [[ "$REFRESH" -eq 1 ]]; then
  echo "Refreshing template catalog cache…"
  run POST /api/platform/template-validation/refresh-catalog-cache
  echo
fi

payload=$(printf '%s\n' "${NAMES[@]}" | jq -R . | jq -s '{names: .}')

echo "Queueing ${#NAMES[@]} migrated templates for smoke test…"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "$payload" | run POST /api/platform/template-validation/validate -d @-
else
  echo "$payload" | curl -sS -X POST "${API}/api/platform/template-validation/validate" \
    "${AUTH[@]}" -d @-
  echo
  echo "Poll status: GET ${API}/api/platform/template-validation/status"
  echo "Per-template progress: GET ${API}/api/platform/template-validation/progress/<name>"
fi

#!/bin/sh
set -eu

CONFIG_DIR="${HERMES_CONFIG_DIR:-/hermes/config}"
CONFIG_FILE="${CONFIG_DIR}/config.hcl"

mkdir -p "${CONFIG_DIR}"

if [ ! -f "${CONFIG_FILE}" ]; then
  PG_HOST="${HERMES_SERVER_POSTGRES_HOST:-localhost}"
  PG_PORT="${HERMES_SERVER_POSTGRES_PORT:-5432}"
  PG_DB="${HERMES_SERVER_POSTGRES_DBNAME:-hermes}"
  PG_USER="${HERMES_SERVER_POSTGRES_USER:-hermes}"
  PG_PASS="${HERMES_SERVER_POSTGRES_PASSWORD:-hermes}"
  BASE_URL="${HERMES_BASE_URL:-${HERMES_SERVER_BASE_URL:-http://localhost:8000}}"
  ALGOLIA_APP_ID="${HERMES_ALGOLIA_APPLICATION_ID:-${HERMES_ALGOLIA_APP_ID:-placeholder-app-id}}"
  ALGOLIA_SEARCH_KEY="${HERMES_ALGOLIA_SEARCH_API_KEY:-placeholder-search-key}"
  ALGOLIA_WRITE_KEY="${HERMES_ALGOLIA_WRITE_API_KEY:-placeholder-write-key}"
  GW_DOMAIN="${HERMES_GOOGLE_WORKSPACE_DOMAIN:-example.com}"
  GW_DOCS="${HERMES_GOOGLE_WORKSPACE_DOCS_FOLDER:-docs-folder-id}"
  GW_DRAFTS="${HERMES_GOOGLE_WORKSPACE_DRAFTS_FOLDER:-drafts-folder-id}"
  GW_SHORTCUTS="${HERMES_GOOGLE_WORKSPACE_SHORTCUTS_FOLDER:-shortcuts-folder-id}"

  cat > "${CONFIG_FILE}" <<EOF
base_url = "${BASE_URL}"
log_format = "standard"

algolia {
  application_id = "${ALGOLIA_APP_ID}"
  docs_index_name = "docs"
  drafts_index_name = "drafts"
  internal_index_name = "internal"
  links_index_name = "links"
  missing_fields_index_name = "missing_fields"
  projects_index_name = "projects"
  search_api_key = "${ALGOLIA_SEARCH_KEY}"
  write_api_key = "${ALGOLIA_WRITE_KEY}"
}

email {
  enabled = false
}

google_workspace {
  create_doc_shortcuts = false
  docs_folder = "${GW_DOCS}"
  domain = "${GW_DOMAIN}"
  drafts_folder = "${GW_DRAFTS}"
  shortcuts_folder = "${GW_SHORTCUTS}"
  oauth2 {
    client_id = "placeholder-client-id"
    hd = "${GW_DOMAIN}"
    redirect_uri = "${BASE_URL}/torii/redirect.html"
  }
}

okta {
  disabled = true
}

postgres {
  dbname = "${PG_DB}"
  host = "${PG_HOST}"
  password = "${PG_PASS}"
  port = ${PG_PORT}
  user = "${PG_USER}"
}

products {
  product "QA" {
    abbreviation = "QA"
  }
}

server {
  addr = "0.0.0.0:8000"
}
EOF
fi

exec /app/hermes "$@" -config="${CONFIG_FILE}"

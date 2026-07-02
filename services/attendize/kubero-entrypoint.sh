#!/bin/bash
set -euo pipefail

APP_ROOT="/usr/share/nginx/html"
STACKBLAZE_BOOTSTRAP_BASE="${STACKBLAZE_BOOTSTRAP_BASE:-https://raw.githubusercontent.com/stackblaze/stack-templates/main/services/attendize}"

log() {
  echo "[attendize-bootstrap] $*"
}

fetch_script() {
  local name="$1"
  local dest="$2"
  if wget -q -O "$dest" "${STACKBLAZE_BOOTSTRAP_BASE}/${name}" 2>/dev/null; then
    return 0
  fi
  if [ -s "$dest" ]; then
    log "Could not fetch ${name}; using existing copy at ${dest}"
    return 0
  fi
  log "ERROR: failed to fetch ${name} from ${STACKBLAZE_BOOTSTRAP_BASE}"
  return 1
}

redis_password_line() {
  local password="${REDIS_PASSWORD:-}"
  if [ "$password" = "null" ] || [ -z "$password" ]; then
    echo 'REDIS_PASSWORD='
  else
    printf 'REDIS_PASSWORD=%s\n' "$password"
  fi
}

sync_env_file() {
  log "Syncing .env from container environment"
  cat > "${APP_ROOT}/.env" <<EOF
APP_NAME=Attendize
APP_ENV=${APP_ENV:-production}
APP_KEY=${APP_KEY:-}
APP_DEBUG=${APP_DEBUG:-false}
APP_URL=${APP_URL:-http://localhost}

LOG_CHANNEL=stack

DB_CONNECTION=${DB_CONNECTION:-mysql}
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-3306}
DB_DATABASE=${DB_DATABASE:-attendize}
DB_USERNAME=${DB_USERNAME:-attendize}
DB_PASSWORD=${DB_PASSWORD:-attendize}

BROADCAST_DRIVER=log
CACHE_DRIVER=${CACHE_DRIVER:-redis}
QUEUE_CONNECTION=${QUEUE_CONNECTION:-redis}
SESSION_DRIVER=${SESSION_DRIVER:-redis}
SESSION_LIFETIME=120

SESSION_SECURE_COOKIE=${SESSION_SECURE_COOKIE:-true}

REDIS_HOST=${REDIS_HOST:-127.0.0.1}
$(redis_password_line)
REDIS_PORT=${REDIS_PORT:-6379}

MAIL_DRIVER=${MAIL_DRIVER:-smtp}
MAIL_HOST=${MAIL_HOST:-smtp.example.com}
MAIL_PORT=${MAIL_PORT:-587}
MAIL_USERNAME=${MAIL_USERNAME:-}
MAIL_PASSWORD=${MAIL_PASSWORD:-}
MAIL_ENCRYPTION=${MAIL_ENCRYPTION:-tls}
MAIL_FROM_ADDRESS=${MAIL_FROM_ADDRESS:-tickets@example.com}
MAIL_FROM_NAME=${MAIL_FROM_NAME:-Attendize}

DEFAULT_DATEPICKER_SEPERATOR="-"
DEFAULT_DATEPICKER_FORMAT="yyyy-MM-dd HH:mm"
DEFAULT_DATETIME_FORMAT="Y-m-d H:i"

WKHTML2PDF_BIN_FILE=wkhtmltopdf-amd64
LOG=errorlog
EOF
}

wait_for_db() {
  log "Waiting for database at ${DB_HOST}:${DB_PORT:-3306}"
  for i in $(seq 1 120); do
    if php -r "
      try {
        new PDO(
          'mysql:host=' . getenv('DB_HOST') . ';port=' . (getenv('DB_PORT') ?: 3306),
          getenv('DB_USERNAME'),
          getenv('DB_PASSWORD')
        );
        exit(0);
      } catch (Exception \$e) {
        exit(1);
      }
    " 2>/dev/null; then
      log "Database is reachable"
      return 0
    fi
    sleep 3
  done
  log "ERROR: database not reachable after 6 minutes"
  exit 1
}

needs_bootstrap() {
  local user_count
  user_count="$(php -r "
    try {
      \$pdo = new PDO(
        'mysql:host=' . getenv('DB_HOST') . ';port=' . (getenv('DB_PORT') ?: 3306) . ';dbname=' . getenv('DB_DATABASE'),
        getenv('DB_USERNAME'),
        getenv('DB_PASSWORD')
      );
      \$stmt = \$pdo->query('SELECT COUNT(*) FROM users');
      echo (int) \$stmt->fetchColumn();
    } catch (Exception \$e) {
      echo 0;
    }
  " 2>/dev/null || echo 0)"

  # DB already has users — skip even when the ephemeral container lost
  # the installed marker file from a prior pod.
  if [ "${user_count}" -gt 0 ]; then
    return 1
  fi

  if [ -f "${APP_ROOT}/installed" ]; then
    return 1
  fi

  return 0
}

mark_installed() {
  if [ -f "${APP_ROOT}/installed" ]; then
    return 0
  fi
  if [ -f VERSION ]; then
    cp VERSION "${APP_ROOT}/installed"
  else
    echo -n "2.8.0" > "${APP_ROOT}/installed"
  fi
}

install_bootstrap_assets() {
  log "Installing bootstrap assets from ${STACKBLAZE_BOOTSTRAP_BASE}"
  fetch_script TrustProxies.php "${APP_ROOT}/app/Http/Middleware/TrustProxies.php"
  fetch_script bootstrap.php "${APP_ROOT}/bootstrap-admin.php"
  fetch_script DemoSeeder.php "${APP_ROOT}/database/seeds/DemoSeeder.php"
  composer dump-autoload --no-interaction --quiet --working-dir="${APP_ROOT}" || true
}

run_bootstrap() {
  cd "${APP_ROOT}"

  if [ "${ATTENDIZE_AUTO_SETUP:-true}" != "true" ]; then
    log "ATTENDIZE_AUTO_SETUP disabled, skipping bootstrap"
    return 0
  fi

  if ! needs_bootstrap; then
    log "Already installed, skipping bootstrap"
    install_bootstrap_assets
    mark_installed
    php artisan config:clear >/dev/null 2>&1 || true
    return 0
  fi

  log "Running first-boot bootstrap"
  install_bootstrap_assets
  sync_env_file

  if [ -z "${APP_KEY:-}" ] || [ "${APP_KEY}" = "base64:" ]; then
    php artisan key:generate --force
  fi

  php artisan migrate --force
  php artisan db:seed --force
  php bootstrap-admin.php
  php artisan db:seed --class=DemoSeeder --force

  mark_installed

  php artisan config:clear
  log "Bootstrap complete"
}

run_worker() {
  cd "${APP_ROOT}"
  sync_env_file
  wait_for_db

  for i in $(seq 1 120); do
    if [ -f "${APP_ROOT}/installed" ]; then
      break
    fi
    log "Worker waiting for web bootstrap to finish..."
    sleep 5
  done

  log "Starting queue worker"
  exec php artisan queue:work redis --sleep=3 --tries=3 --timeout=90
}

cd "${APP_ROOT}"

if [ "${PROC_TYPE:-web}" = "worker" ]; then
  run_worker
fi

sync_env_file
wait_for_db
run_bootstrap
exec /start.sh

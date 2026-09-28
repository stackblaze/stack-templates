#!/bin/bash
# Render the declarative Kong config, then start the gateway.
# Placeholders in kong.yml are ${NAME}. Empty key lines (unset publishable
# keys) are dropped so Kong does not reject the file.
set -euo pipefail

if [ -n "${SUPABASE_SECRET_KEY:-}" ] && [ -n "${SUPABASE_PUBLISHABLE_KEY:-}" ]; then
  export LUA_AUTH_EXPR="\$((headers.authorization ~= nil and headers.authorization:sub(1, 10) ~= 'Bearer sb_' and headers.authorization) or (headers.apikey == '${SUPABASE_SECRET_KEY}' and 'Bearer ${SERVICE_ROLE_KEY_ASYMMETRIC}') or (headers.apikey == '${SUPABASE_PUBLISHABLE_KEY}' and 'Bearer ${ANON_KEY_ASYMMETRIC}') or headers.apikey)"
  export LUA_RT_WS_EXPR="\$((query_params.apikey == '${SUPABASE_SECRET_KEY}' and '${SERVICE_ROLE_KEY_ASYMMETRIC}') or (query_params.apikey == '${SUPABASE_PUBLISHABLE_KEY}' and '${ANON_KEY_ASYMMETRIC}') or query_params.apikey)"
else
  export LUA_AUTH_EXPR="\$((headers.authorization ~= nil and headers.authorization:sub(1, 10) ~= 'Bearer sb_' and headers.authorization) or headers.apikey)"
  export LUA_RT_WS_EXPR="\$(query_params.apikey)"
fi

sed \
  -e "s|\${SUPABASE_ANON_KEY}|${SUPABASE_ANON_KEY}|" \
  -e "s|\${SUPABASE_SERVICE_KEY}|${SUPABASE_SERVICE_KEY}|" \
  -e "s|\${SUPABASE_PUBLISHABLE_KEY}|${SUPABASE_PUBLISHABLE_KEY:-}|" \
  -e "s|\${SUPABASE_SECRET_KEY}|${SUPABASE_SECRET_KEY:-}|" \
  -e "s|\${ANON_KEY_ASYMMETRIC}|${ANON_KEY_ASYMMETRIC:-}|" \
  -e "s|\${SERVICE_ROLE_KEY_ASYMMETRIC}|${SERVICE_ROLE_KEY_ASYMMETRIC:-}|" \
  -e "s|\${LUA_AUTH_EXPR}|${LUA_AUTH_EXPR}|" \
  -e "s|\${LUA_RT_WS_EXPR}|${LUA_RT_WS_EXPR}|" \
  -e "s|\${DASHBOARD_USERNAME}|${DASHBOARD_USERNAME}|" \
  -e "s|\${DASHBOARD_PASSWORD}|${DASHBOARD_PASSWORD}|" \
  /usr/local/kong/template.yml \
  > /usr/local/kong/kong.yml

sed -i '/^[[:space:]]*- key:[[:space:]]*$/d' /usr/local/kong/kong.yml

# Catalog companions are Kubero Services named
# supabase-<role>-<suffix>-kuberoapp (port 80 → the container port).
# This pod is supabase-api-<suffix>-kuberoapp-web-…. Short compose names
# (storage:5000, studio:3000) are not created with the apps, and Kong
# caches the miss.
self="${HOSTNAME%%-kuberoapp-*}"
suffix="${self#supabase-api-}"
sb_svc() { printf 'supabase-%s-%s-kuberoapp' "$1" "$suffix"; }
sed -i \
  -e "s|http://auth:9999|http://$(sb_svc auth)|g" \
  -e "s|http://rest:3000|http://$(sb_svc rest)|g" \
  -e "s|http://realtime-dev.supabase-realtime:4000|http://$(sb_svc realtime)|g" \
  -e "s|http://storage:5000|http://$(sb_svc storage)|g" \
  -e "s|http://functions:9000|http://$(sb_svc functions)|g" \
  -e "s|http://meta:8080|http://$(sb_svc meta)|g" \
  -e "s|http://studio:3000|http://$(sb_svc studio)|g" \
  /usr/local/kong/kong.yml

exec /entrypoint.sh kong docker-start

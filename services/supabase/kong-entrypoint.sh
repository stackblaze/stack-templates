#!/bin/bash
# Supabase API gateway (Kong) entrypoint for StackBlaze. Upstream's
# docker/volumes/api/kong-entrypoint.sh (supabase/supabase master 33c8ab1)
# plus two StackBlaze steps: the legacy anon / service_role keys are signed
# here from this deployment's JWT_SECRET (they are never stored as variables),
# and the compose service names are rewritten to this group's Kubero Services.
# This copy is for reading and diffing; app.yaml embeds the same text.
set -euo pipefail

# --- Legacy API keys: HS256 JWTs signed with JWT_SECRET ---------------------
# Every Supabase service of this deployment derives the same two keys from the
# same secret, with the same fixed claims (Studio, Storage and the functions
# router do it in their own start commands).
b64url() { base64 -w0 | tr '+/' '-_' | tr -d '='; }
hmac_sha256() {
  # stdin: data; $1: key. Kong's image has no openssl CLI everywhere, so fall
  # back to OpenResty's lua-resty-openssl, which Kong itself ships.
  if command -v openssl > /dev/null 2>&1; then
    openssl dgst -sha256 -hmac "$1" -binary
  else
    { printf '%s\n' "$1"; cat; } | resty -e '
      local key = io.read("*l")
      local data = io.read("*a")
      local hmac = assert(require("resty.openssl.hmac").new(key, "sha256"))
      io.write(assert(hmac:final(data)))'
  fi
}
sb_jwt() {
  local h p s
  h=$(printf '%s' '{"alg":"HS256","typ":"JWT"}' | b64url)
  p=$(printf '{"role":"%s","iss":"supabase","iat":1763078400,"exp":2078438400}' "$1" | b64url)
  s=$(printf '%s' "$h.$p" | hmac_sha256 "$JWT_SECRET" | b64url)
  printf '%s.%s.%s' "$h" "$p" "$s"
}
if [ "${#JWT_SECRET}" -lt 32 ]; then
  echo "JWT_SECRET must be at least 32 characters" >&2
  exit 1
fi
SUPABASE_ANON_KEY=$(sb_jwt anon)
SUPABASE_SERVICE_KEY=$(sb_jwt service_role)
# The internal JWTs the opaque sb_ keys are translated to (upstream: the
# asymmetric keys; here the same HS256 keys).
ANON_KEY_ASYMMETRIC=$SUPABASE_ANON_KEY
SERVICE_ROLE_KEY_ASYMMETRIC=$SUPABASE_SERVICE_KEY
export SUPABASE_ANON_KEY SUPABASE_SERVICE_KEY ANON_KEY_ASYMMETRIC SERVICE_ROLE_KEY_ASYMMETRIC

# --- Upstream: Lua expressions for request-transformer ----------------------
if [ -n "${SUPABASE_SECRET_KEY:-}" ] && [ -n "${SUPABASE_PUBLISHABLE_KEY:-}" ]; then
  export LUA_AUTH_EXPR="\$((headers.authorization ~= nil and headers.authorization:sub(1, 10) ~= 'Bearer sb_' and headers.authorization) or (headers.apikey == '$SUPABASE_SECRET_KEY' and 'Bearer $SERVICE_ROLE_KEY_ASYMMETRIC') or (headers.apikey == '$SUPABASE_PUBLISHABLE_KEY' and 'Bearer $ANON_KEY_ASYMMETRIC') or headers.apikey)"
  export LUA_RT_WS_EXPR="\$((query_params.apikey == '$SUPABASE_SECRET_KEY' and '$SERVICE_ROLE_KEY_ASYMMETRIC') or (query_params.apikey == '$SUPABASE_PUBLISHABLE_KEY' and '$ANON_KEY_ASYMMETRIC') or query_params.apikey)"
  export LUA_FUNCTIONS_EXPR="\$((headers.apikey == '$SUPABASE_SECRET_KEY' and '$SERVICE_ROLE_KEY_ASYMMETRIC') or (headers.apikey == '$SUPABASE_PUBLISHABLE_KEY' and '$ANON_KEY_ASYMMETRIC') or (headers.authorization == 'Bearer $SUPABASE_SECRET_KEY' and '$SERVICE_ROLE_KEY_ASYMMETRIC') or (headers.authorization == 'Bearer $SUPABASE_PUBLISHABLE_KEY' and '$ANON_KEY_ASYMMETRIC') or nil)"
else
  export LUA_AUTH_EXPR="\$((headers.authorization ~= nil and headers.authorization:sub(1, 10) ~= 'Bearer sb_' and headers.authorization) or headers.apikey)"
  export LUA_RT_WS_EXPR="\$(query_params.apikey)"
  export LUA_FUNCTIONS_EXPR="\$(nil)"
fi

# --- Upstream: substitute $NAME in the declarative config -------------------
awk '{
  result = ""
  rest = $0
  while (match(rest, /\$[A-Za-z_][A-Za-z_0-9]*/)) {
    varname = substr(rest, RSTART + 1, RLENGTH - 1)
    if (varname in ENVIRON) {
      result = result substr(rest, 1, RSTART - 1) ENVIRON[varname]
    } else {
      result = result substr(rest, 1, RSTART + RLENGTH - 1)
    }
    rest = substr(rest, RSTART + RLENGTH)
  }
  print result rest
}' /usr/local/kong/template.yml > "$KONG_DECLARATIVE_CONFIG"
sed -i '/^[[:space:]]*- key:[[:space:]]*$/d' "$KONG_DECLARATIVE_CONFIG"

# --- StackBlaze: dial this group's Kubero Services --------------------------
# Catalog companions are Kubero Services named supabase-<role>-<suffix>-kuberoapp
# (port 80 → the container port), reachable by their install names.
# SB_NAME_SUFFIX: the group's suffix (set on this card at deploy);
# <hint>-<suffix>-kuberoapp is each service's alias by its install name.
suffix="${SB_NAME_SUFFIX:?SB_NAME_SUFFIX is not set}"
sb_svc() { printf 'supabase-%s-%s-kuberoapp' "$1" "$suffix"; }
if [ "${KONG_REST_READ_REPLICAS:-on}" = "off" ]; then rest_ro=$(sb_svc rest); else rest_ro=$(sb_svc rest-ro); fi
sed -i \
  -e "s|http://auth:9999|http://$(sb_svc auth)|g" \
  -e "s|http://rest-ro:3000|http://$rest_ro|g" \
  -e "s|http://rest:3000|http://$(sb_svc rest)|g" \
  -e "s|http://realtime-dev.supabase-realtime:4000|http://$(sb_svc realtime)|g" \
  -e "s|http://storage:5000|http://$(sb_svc storage)|g" \
  -e "s|http://functions:9000|http://$(sb_svc functions)|g" \
  -e "s|http://meta:8080|http://$(sb_svc meta)|g" \
  -e "s|http://studio:3000|http://$(sb_svc studio)|g" \
  "$KONG_DECLARATIVE_CONFIG"

exec /entrypoint.sh kong docker-start

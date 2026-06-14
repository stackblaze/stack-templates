#!/bin/sh
set -e

# Kubero mounts emptyDir on /tmp, hiding the upstream image's /tmp/docker_run.sh
# and /tmp/data-ps seed. Copy them back before the stock installer runs.
if [ ! -x /tmp/docker_run.sh ]; then
  cp /usr/local/bin/prestashop-docker-run.sh /tmp/docker_run.sh
  chmod +x /tmp/docker_run.sh
fi

if [ -d /usr/local/share/prestashop-seed ] && [ ! -f /var/www/html/index.php ]; then
  cp -n -R -T -p /usr/local/share/prestashop-seed/ /var/www/html/ 2>/dev/null || true
fi

cd /var/www/html
exec /tmp/docker_run.sh

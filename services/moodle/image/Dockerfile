# Moodle publishes no runtime image (Bitnami's moved behind a paywall in 2025),
# so the catalog template runs this one: the official Moodle 5.3.1 release
# package (checksum-pinned) on the official PHP 8.4 Apache image.
#
# - Code is read-only in the image (root-owned). Plugins and upgrades come from
#   a new image, never from the web UI ($CFG->disableupdateautodeploy).
# - moodledata is the template's volume at /var/www/moodledata.
# - config.php reads the database, URL and email from the environment.
# - moodle-start installs Moodle from the command line on the first start (no
#   web installer), runs pending upgrades, then starts Apache. With
#   PROC_TYPE=worker it runs Moodle's cron every minute instead.
FROM docker.io/library/php:8.4.27-apache-bookworm

ARG MOODLE_VERSION=5.3.1
ARG MOODLE_SHA256=820ee2bcd89acc6b91df255b2010bbbab108f29952ab78895a79c4feabf541e7

# PHP extensions Moodle 5.3 needs (public/admin/environment.xml): pgsql, intl,
# zip, gd, soap, exif and opcache on top of the image's built-ins (sodium,
# mbstring, curl, openssl, dom, xml...). Ghostscript is for annotating PDF
# assignment submissions. Build-only packages are removed again.
RUN set -eux; \
  savedAptMark="$(apt-mark showmanual)"; \
  apt-get update; \
  apt-get install -y --no-install-recommends \
    libpq-dev libicu-dev libzip-dev libpng-dev libjpeg62-turbo-dev \
    libfreetype6-dev libwebp-dev libxml2-dev; \
  docker-php-ext-configure gd --with-freetype --with-jpeg --with-webp; \
  docker-php-ext-install -j"$(nproc)" pgsql intl zip gd soap exif opcache; \
  apt-mark auto '.*' > /dev/null; \
  apt-mark manual $savedAptMark; \
  find /usr/local -type f -executable -exec ldd '{}' ';' \
    | awk '/=>/ { so = $(NF-1); if (index(so, "/usr/local/") == 1) { next }; gsub("^/(usr/)?", "", so); printf "*%s\n", so }' \
    | sort -u | xargs -r dpkg-query --search | cut -d: -f1 | sort -u | xargs -rt apt-mark manual; \
  apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
  apt-get install -y --no-install-recommends ghostscript; \
  rm -rf /var/lib/apt/lists/*

RUN set -eux; \
  curl -fsSL -o /tmp/moodle.tgz "https://packaging.moodle.org/stable503/moodle-${MOODLE_VERSION}.tgz"; \
  echo "${MOODLE_SHA256}  /tmp/moodle.tgz" | sha256sum -c -; \
  tar -xzf /tmp/moodle.tgz -C /var/www; \
  rm /tmp/moodle.tgz; \
  grep -q "'${MOODLE_VERSION} " /var/www/moodle/public/version.php; \
  mkdir -p /var/www/moodledata /var/cache/moodle; \
  chown www-data:www-data /var/www/moodledata /var/cache/moodle

# Moodle's own libraries ship in public/lib; upstream also expects the
# Composer runtime dependencies (vendor/, outside the web root) installed from
# its composer.lock, without the developer packages.
COPY --from=docker.io/library/composer:2.11.2 /usr/bin/composer /usr/local/bin/composer
RUN set -eux; \
  cd /var/www/moodle; \
  COMPOSER_ALLOW_SUPERUSER=1 composer install --no-dev --classmap-authoritative --no-interaction --no-progress; \
  rm -rf /usr/local/bin/composer /root/.composer /root/.cache

COPY config.php /var/www/moodle/config.php
COPY php.ini /usr/local/etc/php/conf.d/moodle.ini
COPY apache.conf /etc/apache2/sites-available/000-default.conf
COPY stackblaze-install.php /usr/local/lib/stackblaze/install.php
COPY moodle-start /usr/local/bin/moodle-start
RUN set -eux; \
  chmod 0755 /usr/local/bin/moodle-start; \
  a2enmod rewrite headers remoteip > /dev/null; \
  echo 'ServerName localhost' > /etc/apache2/conf-enabled/servername.conf; \
  php -l /var/www/moodle/config.php; php -l /usr/local/lib/stackblaze/install.php

WORKDIR /var/www/moodle
EXPOSE 80
CMD ["/usr/local/bin/moodle-start"]

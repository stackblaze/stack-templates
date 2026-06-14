FROM prestashop/prestashop:8-apache

USER root
RUN cp /tmp/docker_run.sh /usr/local/bin/prestashop-docker-run.sh \
    && mkdir -p /usr/local/share/prestashop-seed \
    && cp -a /tmp/data-ps/prestashop/. /usr/local/share/prestashop-seed/
COPY kubero-entrypoint.sh /usr/local/bin/kubero-entrypoint.sh
RUN chmod +x /usr/local/bin/kubero-entrypoint.sh /usr/local/bin/prestashop-docker-run.sh

ENTRYPOINT ["/usr/local/bin/kubero-entrypoint.sh"]

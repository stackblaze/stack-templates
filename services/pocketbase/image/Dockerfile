# PocketBase for the StackBlaze catalog.
#
# Upstream publishes release binaries, not a container image, and its docs
# suggest exactly this: a small Alpine image that downloads the release zip
# (https://pocketbase.io/docs/going-to-production/#using-docker). We pin the
# version and check the zip against upstream's checksums.txt.
FROM alpine:3.22

ARG PB_VERSION=0.40.6
ARG PB_SHA256=0e1f609158ed945f809f8a02ae012aa0427129c66ebb63c1aee76f2c0309373f

RUN apk add --no-cache ca-certificates tzdata \
 && apk add --no-cache --virtual .fetch unzip wget \
 && wget -q -O /tmp/pb.zip "https://github.com/pocketbase/pocketbase/releases/download/v${PB_VERSION}/pocketbase_${PB_VERSION}_linux_amd64.zip" \
 && echo "${PB_SHA256}  /tmp/pb.zip" | sha256sum -c - \
 && unzip -q /tmp/pb.zip pocketbase -d /pb \
 && rm /tmp/pb.zip \
 && apk del .fetch \
 && addgroup -g 1000 pocketbase \
 && adduser -D -H -u 1000 -G pocketbase -h /pb pocketbase \
 && mkdir -p /pb/pb_data \
 && chown pocketbase:pocketbase /pb/pb_data

# StackBlaze boot hook (first superuser, add-on mail, public URL). It lives in
# the image, read-only to the app user: superusers cannot add or edit hooks.
COPY pb_hooks /pb/pb_hooks

USER 1000:1000
WORKDIR /pb
EXPOSE 8090
VOLUME /pb/pb_data

# --encryptionEnv: settings (SMTP password, OAuth2 secrets, S3 keys) are stored
# AES-256 encrypted with the 32-character key in PB_ENCRYPTION_KEY.
ENTRYPOINT ["/pb/pocketbase"]
CMD ["serve", "--http=0.0.0.0:8090", "--dir=/pb/pb_data", "--hooksDir=/pb/pb_hooks", "--encryptionEnv=PB_ENCRYPTION_KEY"]

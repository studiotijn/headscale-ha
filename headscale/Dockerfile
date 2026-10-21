# syntax=docker/dockerfile:1
# https://contributors.home-assistant.io/apps/guides/dockerfile/
#
# Upstream components are pinned; bump them together with CHANGELOG.md.
ARG HEADPLANE_IMAGE=ghcr.io/tale/headplane:0.8.1
ARG TAILSCALE_IMAGE=ghcr.io/tailscale/tailscale:v1.104.2
ARG BUILD_FROM=ghcr.io/home-assistant/base:3.23

FROM ${HEADPLANE_IMAGE} AS headplane
FROM ${TAILSCALE_IMAGE} AS tailscale

FROM ${BUILD_FROM}

ARG TARGETARCH
ARG HEADSCALE_VERSION=0.29.5
ARG HEADSCALE_SHA256_AMD64=e979d27fe17d924d33bb6ab7504f6338d0635989a0cfdcfbc0ceb637dbcbe980
ARG HEADSCALE_SHA256_ARM64=3afddd207b89ac22cfad4235cc163c6e538cc59ada139e7c0bf47640c5d9e945

# Runtime packages: Node.js for Headplane, Python for the ingress UI and
# bootstrap logic, iptables/ip6tables for kernel-mode Tailscale.
RUN apk add --no-cache \
        ca-certificates \
        iproute2 \
        iptables \
        ip6tables \
        nodejs \
        python3 \
        py3-pip \
        tzdata

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# Headscale: official static release binary, checksum-verified.
RUN set -eux; \
    case "${TARGETARCH}" in \
        amd64) sha="${HEADSCALE_SHA256_AMD64}" ;; \
        arm64) sha="${HEADSCALE_SHA256_ARM64}" ;; \
        *) echo "Unsupported TARGETARCH: ${TARGETARCH:-unset} (use Docker BuildKit)"; exit 1 ;; \
    esac; \
    curl -fsSL -o /usr/bin/headscale \
        "https://github.com/juanfont/headscale/releases/download/v${HEADSCALE_VERSION}/headscale_${HEADSCALE_VERSION}_linux_${TARGETARCH}"; \
    echo "${sha}  /usr/bin/headscale" | sha256sum -c -; \
    chmod 0755 /usr/bin/headscale; \
    headscale version

# Tailscale client (subnet router / exit node) from the official image.
COPY --from=tailscale /usr/local/bin/tailscale /usr/local/bin/tailscaled /usr/bin/

# Headplane web UI (pure JavaScript build, runs on Alpine's Node.js).
COPY --from=headplane /app /app

RUN addgroup -S headplane && adduser -S -D -H -G headplane -s /sbin/nologin headplane

COPY rootfs /

RUN chmod 0755 /etc/s6-overlay/s6-rc.d/*/run /etc/s6-overlay/s6-rc.d/*/finish \
        /etc/s6-overlay/scripts/*.sh 2>/dev/null || true; \
    python3 -m compileall -q /usr/lib/hsha

ENV PYTHONPATH=/usr/lib \
    PYTHONUNBUFFERED=1

LABEL \
    org.opencontainers.image.title="Home Assistant App: Headscale" \
    org.opencontainers.image.description="Headscale, Headplane, subnet router and remote printing for Home Assistant." \
    org.opencontainers.image.source="https://github.com/studiotijn/headscale-ha" \
    org.opencontainers.image.licenses="Apache-2.0"

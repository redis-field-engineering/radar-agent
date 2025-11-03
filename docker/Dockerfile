FROM debian:bookworm-slim

ARG BINARY

LABEL org.opencontainers.image.source="https://github.com/redis-field-engineering/radar-collector" \
  org.opencontainers.image.licenses="Redis, Inc." \
  org.opencontainers.image.authors="Radar Team"

# Install required packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libssl3 \
    ca-certificates \
    curl && \
    rm -rf /var/lib/apt/lists/* && \
    adduser --disabled-password --gecos "" appuser

# Create necessary directories
RUN mkdir -p /certs /etc/collector /home/appuser/bin && \
    chown -R appuser:appuser /certs /etc/collector /home/appuser

# Copy default config (customers may override via volume)
COPY --chown=appuser:appuser radar-collector-config-sample.yml /etc/collector/config.yaml

# Copy the collector binary
COPY ${BINARY} /usr/local/bin/radar-collector
RUN chmod +x /usr/local/bin/radar-collector

USER appuser

# Environment defaults
ENV COLLECTOR_CONFIG=/etc/collector/config.yaml \
    COLLECTOR_TLS_CERT=/certs/server.pem \
    COLLECTOR_TLS_KEY=/certs/server.key

# Expose volumes for certs and config
VOLUME ["/certs", "/etc/collector"]

# Healthcheck for orchestrators
HEALTHCHECK --interval=30s --timeout=5s \
  CMD ["radar-collector", "--health"] || exit 1

ENTRYPOINT ["radar-collector"]
CMD ["--config", "/etc/collector/config.yaml"]

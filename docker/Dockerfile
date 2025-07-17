FROM debian:bookworm-slim

ARG BINARY

LABEL org.opencontainers.image.source="https://github.com/redis-field-engineering/radar-agent" \
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
RUN mkdir -p /certs /etc/agent /home/appuser/bin && \
    chown -R appuser:appuser /certs /etc/agent /home/appuser

# Copy default config (customers may override via volume)
COPY --chown=appuser:appuser radar-agent-config-sample.yml /etc/agent/config.yaml

# Copy the agent binary
COPY ${BINARY} /usr/local/bin/radar-agent
RUN chmod +x /usr/local/bin/radar-agent

USER appuser

# Environment defaults
ENV AGENT_CONFIG=/etc/agent/config.yaml \
    AGENT_TLS_CERT=/certs/server.pem \
    AGENT_TLS_KEY=/certs/server.key

# Expose volumes for certs and config
VOLUME ["/certs", "/etc/agent"]

# Healthcheck for orchestrators
HEALTHCHECK --interval=30s --timeout=5s \
  CMD ["/usr/local/bin/radar-agent", "--health"] || exit 1

ENTRYPOINT ["/usr/local/bin/radar-agent"]
CMD ["--config", "/etc/agent/config.yaml"]

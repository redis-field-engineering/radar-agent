FROM rust:1.88-slim AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    protobuf-compiler \
    pkg-config \
    libssl-dev \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

ENV CARGO_HOME=/cargo
WORKDIR /app

COPY proto ./proto
COPY agent ./agent

WORKDIR /app/agent
RUN cargo build --release

FROM debian:bookworm-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libssl3 \
    ca-certificates \
    curl && \
    rm -rf /var/lib/apt/lists/* && \
    adduser --disabled-password --gecos "" appuser

COPY --from=builder /app/agent/target/release/radar-agent /usr/local/bin/radar-agent

ENV AGENT_TLS_CERT=/certs/server.pem
ENV AGENT_TLS_KEY=/certs/server.key

USER appuser

ENTRYPOINT ["/usr/local/bin/radar-agent"]

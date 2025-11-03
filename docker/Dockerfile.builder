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
COPY collector ./collector

WORKDIR /app/collector
RUN cargo build --release

FROM debian:bookworm-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libssl3 \
    ca-certificates \
    curl && \
    rm -rf /var/lib/apt/lists/* && \
    adduser --disabled-password --gecos "" appuser

COPY --from=builder /app/collector/target/release/radar-collector /usr/local/bin/radar-collector

ENV COLLECTOR_TLS_CERT=/certs/server.pem
ENV COLLECTOR_TLS_KEY=/certs/server.key

USER appuser

ENTRYPOINT ["/usr/local/bin/radar-collector"]

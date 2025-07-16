# Docker Files for Radar Agent

This directory contains Docker configurations for packaging and deploying the Radar Agent using pre-built binaries.

## Available Images

### `Dockerfile` (Debian)
**Target**: Production deployments with standard glibc
- **Base**: `debian:bookworm-slim`
- **Binary**: Pre-built radar-agent-linux (glibc)
- **Use Cases**: Modern Linux distributions, Kubernetes, Docker Compose
- **Registry**: `ghcr.io/redis-field-engineering/radar-agent:debian-latest`

### `Dockerfile.alpine` (Alpine)
**Target**: Minimal deployments with musl libc
- **Base**: `alpine:3.18`
- **Binary**: Pre-built radar-agent-linux-musl (musl)
- **Use Cases**: Alpine Linux, minimal containers, embedded systems
- **Registry**: `ghcr.io/redis-field-engineering/radar-agent:alpine-latest`

## Quick Start

```bash
# Pull latest Alpine image (recommended)
docker pull ghcr.io/redis-field-engineering/radar-agent:alpine-latest

# Pull latest Debian image
docker pull ghcr.io/redis-field-engineering/radar-agent:debian-latest

# Run with default config
docker run --rm ghcr.io/redis-field-engineering/radar-agent:alpine-latest --help

# Run with custom config
docker run -v $(pwd)/my-config.yaml:/etc/agent/config.yaml \
  ghcr.io/redis-field-engineering/radar-agent:alpine-latest
```

## Image Selection Guide

| Environment | Recommended Image | Rationale |
|-------------|------------------|-----------|
| **Kubernetes** | Alpine or Debian | Both work well, Alpine is smaller |
| **Docker Compose** | Alpine | Recommended for most use cases |
| **Alpine Linux** | Alpine | Native musl libc support |
| **Legacy Systems** | Alpine | Static binary, fewer dependencies |
| **ARM64/Apple Silicon** | Alpine or Debian | Multi-arch support available |

## Build Process

Images are built automatically via GitHub Actions when triggered by the main radar repository:

1. **Binary Source**: Pre-built binaries from `redis-field-engineering/radar` repository
2. **Trigger**: Repository dispatch event `radar-agent-built`
3. **Build**: Docker images built and pushed to GitHub Container Registry
4. **No source code required**: Only binaries and configuration files

## Environment Variables

All images support these environment variables:
- `AGENT_TLS_CERT` - Path to TLS certificate (default: `/certs/server.pem`)
- `AGENT_TLS_KEY` - Path to TLS private key (default: `/certs/server.key`)
- `RUST_LOG` - Log level override (e.g., `debug`, `info`)

## Security

- All images run as non-root user `appuser` (UID 1000)
- Minimal attack surface with only essential packages
- TLS support built-in for secure communication
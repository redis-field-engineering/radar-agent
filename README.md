# Radar Agent

A telemetry agent that collects Redis metrics from configured deployments and sends them to a gRPC server for monitoring and analysis.

## Overview

Radar Agent connects to one or more Redis instances or deployments, collects metrics and configuration data at regular intervals, and forwards this data to a central gRPC server. The agent supports various Redis deployment types including:

- Standalone instances
- Redis Enterprise clusters
- OSS clusters

## Installation

### Pre-built Binaries

This document is distributed with a pre-built binary called `agent`.

## Configuration

The agent is configured using a YAML file. By default, it looks for `agent.yaml` in the current directory, but you can specify a different file using the `--config` command-line option.

### Basic Configuration Example

```yaml
agent:
  # Unique identifier for this agent instance
  id: "agent-1"
  # Hostname for this agent (defaults to system hostname if not specified)
  hostname: "redis-telemetry-node"
  # Key-value labels to attach to this agent
  labels:
    env: "production"
    region: "us-west-2"
  # Log level: trace, debug, info, warn, error
  log_level: "info"
  # Collection interval with time unit (s, m, h)
  collection_interval: "60s"

server:
  # URL of the Radar server's gRPC endpoint
  grpc_url: "https://grpc.radar.redis.io:443"
  # API key for authenticating with the Radar server
  api_key: "your-api-key-here"
  # Send interval with time unit (s, m, h)
  send_interval: "60s"
  # Maximum number of batches to queue
  max_batch_size: 100

# Redis Standalone Instance
deployments:
  - id: "redis-prod-1"
    name: "Production Redis"
    type: "STANDALONE"
    redis_url: "redis://redis.example.com:6379"
```

### Deployment Configuration

The agent can monitor different types of Redis deployments:

#### Standalone Redis Instance

```yaml
deployments:
  - id: "redis-standalone"
    name: "Standalone Redis"
    type: "STANDALONE"
    redis_url: "redis://redis.example.com:6379"
```

#### Redis Cluster

```yaml
deployments:
  - id: "redis-cluster"
    name: "Redis Cluster"
    type: "CLUSTER"
    redis_urls:
      - "redis://redis-cluster-0.example.com:6379"
      - "redis://redis-cluster-1.example.com:6379"
    auto_discover: true
```

#### Redis Enterprise

```yaml
deployments:
  - id: "redis-enterprise"
    name: "Redis Enterprise"
    type: "ENTERPRISE"
    redis_url: "redis://redis-enterprise.example.com:12000"
    rest_api:
      host: "redis-enterprise.example.com"
      port: 9443
    credentials:
      # Redis authentication (applied to all redis_urls without auth)
      redis:
        username: "default"
        password: "redis_password123"
      # Enterprise REST API authentication
      enterprise_api:
        basic_auth: "admin@cluster.local:password123"
```

### Credentials and Environment Variables

The `credentials` section allows you to specify authentication information for Redis instances and REST APIs. You can use environment variables for sensitive information:

```yaml
credentials:
  redis:
    username: "${REDIS_USERNAME}"
    password: "${REDIS_PASSWORD}"
  enterprise_api:
    basic_auth: "${REDIS_ENTERPRISE_AUTH}"
  cloud_api:
    account_key: "${REDIS_CLOUD_ACCOUNT_KEY}"
    user_key: "${REDIS_CLOUD_USER_KEY}"
```

When a Redis URL doesn't include authentication, the agent will automatically apply the credentials from the `redis` section. If a Redis URL already includes authentication (e.g., `redis://user:pass@host:port`), those credentials will be preserved.

### Environment Variable Overrides

Configuration values can be overridden using environment variables:

```bash
# Override agent ID
export AGENT_AGENT_ID="custom-agent-id"

# Override deployment name (for the first deployment)
export AGENT_DEPLOYMENTS_0_NAME="custom-deployment-name"

# Override server URL
export AGENT_SERVER_GRPC_URL="https://new-server.example.com:50051"
```

## Running the Agent

### Command Line Options

| Option     | Env Variable   | Description                | Default      |
| ---------- | -------------- | -------------------------- | ------------ |
| `--config` | `AGENT_CONFIG` | Path to configuration file | `agent.yaml` |

### Examples

```bash
# Run with default configuration file
agent

# Specify a different configuration file
agent --config /path/to/custom-config.yaml
```

### Logging

The log level can be configured in the configuration file or using the `RUST_LOG` environment variable:

```bash
# Set log level to debug
RUST_LOG=debug agent
```

Available log levels: `error`, `warn`, `info`, `debug`, `trace` (from least to most verbose).

## Troubleshooting

### Common Issues

1. **Connection Refused**: Ensure that the Redis instance is running and accessible from the agent.
2. **Authentication Failed**: Check that the credentials in your configuration are correct.
3. **Server Connection Issues**: Verify that the gRPC server URL is correct and the server is running.

### Checking Agent Status

The agent logs its status to the console. You can increase the log level to get more detailed information:

```bash
RUST_LOG=debug agent
```

## Support

For issues, questions, or feedback, please contact radar-support@redis.com.


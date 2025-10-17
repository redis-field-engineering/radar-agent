# Radar Agent

A telemetry agent that collects Redis metrics from configured deployments and sends them to a gRPC server for monitoring and analysis.

## Overview

Radar Agent connects to one or more Redis instances or deployments, collects metrics and configuration data at regular intervals, and forwards this data to a central gRPC server. The agent supports various Redis deployment types including:

- Standalone instances
- Redis Enterprise clusters
- OSS clusters

## Documentation

For complete documentation including installation, configuration, and usage instructions, please visit:

**[https://redis-field-engineering.github.io/radar/](https://redis-field-engineering.github.io/radar/)**

## Releases

Docker images and pre-built binaries are available from the [releases page](https://github.com/redis-field-engineering/radar-agent/releases).

## Support

For issues, questions, or feedback:
- Open an issue on [GitHub](https://github.com/redis-field-engineering/radar-agent/issues)
- Contact: radar-support@redis.com


# Redis Enterprise Agent Provisioning Tool

This utility helps create and manage permissions in Redis Enterprise for the Radar agent. It can provision multiple Redis Enterprise clusters with the necessary ACLs, roles, users, and database permissions for agent monitoring.

## Features

- **Multi-cluster provisioning** from YAML configuration files
- **Interactive mode** for single cluster provisioning
- **Environment variable interpolation** in YAML configs using `${ENV_VAR}` syntax
- **Flexible permission management** with custom ACL rules and role levels
- **Database filtering** with regex patterns
- **SSL verification** options for production environments
- **Standalone executable** build support

## Quick Start

### Interactive Mode
```bash
python3 enterprise_credentials.py
```

or if using the standalone binary

```bash
./enterprise_credentials
```

### Command Line Mode
```bash
# Single cluster
python3 enterprise_credentials.py --endpoint https://localhost:9443 \
  --username admin@re.demo --password redis123 \
  --agent-name radar-agent --agent-password radar##123 --create

# Multi-cluster from YAML config
python3 enterprise_credentials.py --agent-yaml-config agent-config.yaml \
  --agent-name radar-agent --agent-password radar##123 --create
```

## Configuration

### Pulling from Agent Config

The tool supports pulling Redis Enterprise endpoints from the Radar agent config.  It will iterate over the deployments looking for the ENTERPRISE type and use the information there to connect to the Redis Enterprise cluster and provision agent access.

```yaml
deployment:
  - id: "production-cluster"
    name: "Production Redis"
    type: "ENTERPRISE"
    rest_api:
      host: "redis.company.com"
      port: 9443
    credentials:
      enterprise_api:
        basic_auth: "${ADMIN_USER}:${ADMIN_PASSWORD}"
  - id: "staging-cluster"
    name: "Staging Redis"
    type: "ENTERPRISE"
    redis_urls: "redis://redis-1200.staging.example.com:12000"
    rest_api:
      port: 9443
    credentials:
      enterprise_api:
        basic_auth: "${STAGING_USER}:${STAGING_PASSWORD}"
```

### Environment Variables

Set environment variables to avoid hardcoding credentials:

```bash
export ADMIN_USER=admin@re.demo
export ADMIN_PASSWORD=redis123
export AGENT_NAME=radar-agent
export AGENT_PASSWORD=radar123
```

## Usage Examples

### Create New Agent Permissions
```bash
# Interactive mode
python3 enterprise_credentials.py

# Command line with custom ACL rules
python3 enterprise_credentials.py --endpoint https://redis.company.com:9443 \
  --username admin@company.com --password secure123 \
  --agent-name monitoring-agent \
  --acl-rules "+@read +info +ping +config|get +client|list +memory +latency +slowlog" \
  --create
```

### Update Existing Permissions
```bash
# Update permissions for existing agent
python3 enterprise_credentials.py --agent-name radar-agent --update

# Update only production databases
python3 enterprise_credentials.py --agent-name radar-agent \
  --update --database-filter "prod-.*" --skip-existing
```

### Multi-Cluster Provisioning
```bash
# Provision all ENTERPRISE deployments in config
python3 enterprise_credentials.py --agent-yaml-config agent-config.yaml \
  --agent-name radar-agent --create

# Force recreation of existing components
python3 enterprise_credentials.py --agent-yaml-config agent-config.yaml \
  --agent-name radar-agent --create --force
```

### Production Environment
```bash
# Enable SSL verification for production
python3 enterprise_credentials.py --endpoint https://redis.company.com:9443 \
  --verify-ssl --agent-name prod-agent --create

# Skip database permissions (only create ACL, role, user)
python3 enterprise_credentials.py --agent-name radar-agent \
  --create --skip-all-databases
```

## Command Line Options

### Connection Options
- `--endpoint`: Redis Enterprise REST API endpoint
- `--username`: Admin username
- `--password`: Admin password
- `--verify-ssl`: Enable SSL certificate verification

### Agent Options
- `--agent-yaml-config`: Path to agent YAML config file
- `--agent-name`: Agent name for permissions
- `--agent-password`: Agent password
- `--agent-email`: Agent email (default: agent-name@example.com)

### ACL Options
- `--acl-rules`: ACL rules for the agent (default: monitoring permissions)

### Role Options
- `--role-management`: Role management level (default: cluster_member)

### Action Options
- `--create`: Force create new agent permissions
- `--update`: Force update existing agent permissions
- `--force`: Force recreation of existing components

### Database Options
- `--database-filter`: Only update databases matching regex pattern
- `--skip-existing`: Skip databases that already have permission
- `--skip-all-databases`: Skip applying permissions to databases

## Troubleshooting

### Common Issues

1. **SSL Certificate Errors**
   - Use `--verify-ssl` for production environments
   - Default behavior skips SSL verification for development

2. **Permission Denied**
   - Ensure admin credentials have sufficient privileges
   - Check that the user can create ACLs, roles, and users

3. **Component Already Exists**
   - Use `--force` to recreate existing components
   - Use `--update` to update existing permissions

4. **Environment Variables Not Set**
   - The tool will warn about missing environment variables
   - Original `${ENV_VAR}` patterns are preserved if not set



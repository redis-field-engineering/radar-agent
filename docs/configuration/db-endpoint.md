# Redis Enterprise Preferred Database Endpoint Configuration

This configuration is used in combination with `auto_discover: true` to guide the agent which of the Redis Enterprise database endpoints to use.

Inside the `enterprise` configuration section there  flexible endpoint selection based on actual BDBS API endpoint data.

## Complete Configuration Options

```yaml
deployments:
  - id: "redis-enterprise-prod"
    name: "Production Enterprise Cluster"
    type: "ENTERPRISE"

    enterprise:
      db_endpoint: "external_ip"  # Choose one of the 4 options below
      
    rest_api:
      host: "redis-enterprise.example.com"
      port: 9443
    credentials:
      rest_api:
        basic_auth: "admin:password"
```

## Available Options

| Option | Description | When to Use | Example Result |
|--------|-------------|-------------|----------------|
| `internal_dns` | Use internal DNS names | Kubernetes, internal networks | `redis://db-node-1.internal:12000` |
| `internal_ip` | Use internal IP addresses | Direct internal connections | `redis://10.0.1.100:12000` |
| `external_dns` | Use external DNS names | Cross-datacenter, public access | `redis://db-node-1.example.com:12000` |
| `external_ip` | Use external IP addresses | **DEFAULT** - Most reliable | `redis://203.0.113.100:12000` |

## How It Works: BDBS API Response Mapping

The agent calls the Redis Enterprise REST API `/v1/bdbs` endpoint and receives endpoint information for each database. Here's how each configuration option maps to the JSON response:

### Sample BDBS API Response
```json
[
  {
    "uid": 1,
    "name": "production-db",
    "port": 12000,
    "memory_size": 52428800,
    "tls_mode": "disabled",
    "endpoints": [
      {
        "addr": ["172.18.0.5"],              // internal_ip/external_ip uses this
        "addr_type": "external",             // Common in Docker/single-node setups
        "dns_name": "redis-12000.cluster.local", // internal_dns/external_dns uses this
        "port": 12000
      }
    ]
  },
  {
    "uid": 2,
    "name": "cache-db", 
    "port": 12001,
    "memory_size": 107374182,
    "tls_mode": "enabled",
    "endpoints": [
      {
        "addr": ["172.18.0.5"],              // Same host, different port
        "addr_type": "external",
        "dns_name": "redis-12001.cluster.local", // Port-specific DNS
        "port": 12001
      }
    ]
  }
]
```

### Configuration → Result Mapping

#### Option 1: `external_dns` (Most Common)
```yaml
enterprise:
  db_endpoint: "external_dns"
```
**Selects**: `endpoints[0].dns_name` where `addr_type == "external"`  
**Results**: 
- `redis://redis-12000.cluster.local:12000/12000`
- `rediss://redis-12001.cluster.local:12001/12001` (TLS enabled)
**Use Case**: Docker/Kubernetes environments, load balancers

#### Option 2: `external_ip` (DEFAULT)
```yaml
enterprise:
  db_endpoint: "external_ip"
```
**Selects**: `endpoints[0].addr[0]` where `addr_type == "external"`  
**Results**:
- `redis://172.18.0.5:12000/12000`
- `rediss://172.18.0.5:12001/12001` (TLS enabled)
**Use Case**: Most reliable, direct IP connections

#### Option 3: `internal_dns` (Fallback)
```yaml
enterprise:
  db_endpoint: "internal_dns"
```
**Selects**: `endpoints[0].dns_name` where `addr_type == "internal"`  
**Results**: Falls back to REST API host when no internal endpoints
- `redis://localhost:12000/12000` (fallback behavior)
**Use Case**: When true internal endpoints are available

#### Option 4: `internal_ip` (Fallback)
```yaml
enterprise:
  db_endpoint: "internal_ip"
```
**Selects**: `endpoints[0].addr[0]` where `addr_type == "internal"`  
**Results**: Falls back to REST API host when no internal endpoints
- `redis://localhost:12000/12000` (fallback behavior)
**Use Case**: When true internal endpoints are available

## Real-World Deployment Examples

### Docker/Local Development
```yaml
enterprise:
  db_endpoint: "external_dns"
# Result: redis://redis-12000.cluster.local:12000
# Uses Docker DNS, works across containers
```

### Production Reliability (Default)
```yaml
enterprise:
  db_endpoint: "external_ip"  
# Result: redis://172.18.0.5:12000
# Direct IP connection, most reliable
```

### Kubernetes Service Discovery
```yaml
enterprise:
  db_endpoint: "external_dns"
# Result: redis://redis-12000.cluster.local:12000
# Works with Kubernetes service mesh
```

### Multi-Database Monitoring
```yaml
enterprise:
  db_endpoint: "external_dns"
# Results:
# - redis://redis-12000.cluster.local:12000 (database 1)
# - rediss://redis-12001.cluster.local:12001 (database 2, TLS)
# Each database gets its own DNS name
```

## TLS Support
When `tls_mode: "enabled"` in the BDBS response:
```yaml
enterprise:
  db_endpoint: "external_ip"
# Result: rediss://172.18.0.5:12001/12001  # Note "rediss://" for TLS
```

## Fallback Behavior
If the preferred endpoint type isn't available:
```yaml
enterprise:
  db_endpoint: "internal_dns"  # Requested internal DNS
# If no internal endpoints available:
# Falls back to: redis://localhost:12000  # Uses REST API host
#
# If external endpoint has empty dns_name:
# Falls back to: redis://172.18.0.5:12000  # Uses IP instead
```
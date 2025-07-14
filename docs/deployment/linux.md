# Redis Radar Agent Deployment Guide for Linux

This guide covers deployment methods for the `redis-radar-agent` binary on Linux systems with systemd (Ubuntu 18.04+, RHEL/CentOS 7+, Fedora, etc.).

## Prerequisites

- Built `redis-radar-agent` binary
- `agent.yml` configuration file
- Linux system with systemd (Ubuntu 18.04+, RHEL/CentOS 7+, Fedora, etc.)

## Distribution-Specific Notes

### RHEL/CentOS 7+
- SELinux may be enabled by default. If you encounter permission issues, check SELinux status:
  ```bash
  sestatus
  getenforce
  ```
- To allow the service to write to log files with SELinux enabled:
  ```bash
  sudo setsebool -P httpd_can_network_connect 1
  sudo semanage fcontext -a -t admin_home_t "/var/log/redis-radar-agent(/.*)?"
  sudo restorecon -R /var/log/redis-radar-agent
  ```
- Package management uses `yum` (RHEL/CentOS 7) or `dnf` (RHEL/CentOS 8+):
  ```bash
  # Install logrotate if not present
  sudo yum install logrotate
  # or
  sudo dnf install logrotate
  ```

### Ubuntu/Debian
- Package management uses `apt`:
  ```bash
  # Install logrotate if not present
  sudo apt update && sudo apt install logrotate
  ```

## Quick Start - Background Execution

For simple background execution during development or testing:

```bash
# Run in background with logs redirected to file
nohup ./redis-radar-agent --config ./agent.yml > /var/log/redis-radar.log 2>&1 &

# Check if running
ps aux | grep redis-radar-agent

# View logs
tail -f redis-radar.log

# Stop the process
pkill redis-radar-agent
```

To run with a specific config file location:

```bash
nohup ./redis-radar-agent --config /path/to/your/agent.yml > /var/log/redis-radar.log 2>&1 &
```

## Production Deployment with systemd

### 1. Create Directory Structure

```bash
# Create application directory
sudo mkdir -p /opt/redis-radar-agent

# Create configuration directory
sudo mkdir -p /etc/redis-radar-agent

# Create log directory
sudo mkdir -p /var/log/redis-radar-agent
```

### 2. Install Files

```bash
# Copy binary to application directory
sudo cp ./redis-radar-agent /opt/redis-radar-agent/

# Copy configuration to system config directory
sudo cp ./agent.yml /etc/redis-radar-agent/

# Set appropriate permissions
sudo chown -R root:root /opt/redis-radar-agent
sudo chmod 755 /opt/redis-radar-agent/redis-radar-agent
sudo chown -R root:root /etc/redis-radar-agent
sudo chmod 644 /etc/redis-radar-agent/agent.yml
```

### 3. Create systemd Service

Create the service file at `/etc/systemd/system/redis-radar-agent.service`:

```ini
[Unit]
Description=Redis Radar Agent
Documentation=https://github.com/your-org/redis-radar-agent
After=network.target
Wants=network.target

[Service]
Type=simple
User=nobody
Group=nogroup
WorkingDirectory=/opt/redis-radar-agent
ExecStart=/opt/redis-radar-agent/redis-radar-agent --config /etc/redis-radar-agent/agent.yml
Restart=always
RestartSec=10
TimeoutStartSec=30
TimeoutStopSec=30

# Logging
StandardOutput=append:/var/log/redis-radar-agent/redis-radar-agent.log
StandardError=append:/var/log/redis-radar-agent/redis-radar-agent.log

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/redis-radar-agent

[Install]
WantedBy=multi-user.target
```

### 4. Configure Log Rotation

Create log rotation configuration at `/etc/logrotate.d/redis-radar-agent`:

```
/var/log/redis-radar-agent/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 nobody nogroup
    postrotate
        /bin/systemctl reload redis-radar-agent.service > /dev/null 2>&1 || true
    endscript
}
```

### 5. Enable and Start Service

```bash
# Set correct permissions for log directory
sudo chown -R nobody:nogroup /var/log/redis-radar-agent

# Reload systemd configuration
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable redis-radar-agent.service

# Start the service
sudo systemctl start redis-radar-agent.service

# Check service status
sudo systemctl status redis-radar-agent.service
```

## Service Management

### Check Service Status
```bash
sudo systemctl status redis-radar-agent.service
```

### View Logs
```bash
# Follow live logs
sudo journalctl -u redis-radar-agent.service -f

# View recent logs
sudo journalctl -u redis-radar-agent.service -n 100

# View logs since specific time
sudo journalctl -u redis-radar-agent.service --since "2024-01-01 00:00:00"

# View application logs directly
sudo tail -f /var/log/redis-radar-agent/redis-radar-agent.log
```

### Restart Service
```bash
sudo systemctl restart redis-radar-agent.service
```

### Stop Service
```bash
sudo systemctl stop redis-radar-agent.service
```

### Disable Service
```bash
sudo systemctl disable redis-radar-agent.service
```

## Configuration Management

### Update Configuration
```bash
# Edit configuration
sudo nano /etc/redis-radar-agent/agent.yml

# Restart service to apply changes
sudo systemctl restart redis-radar-agent.service
```

### Validate Configuration
```bash
# Test configuration before applying
/opt/redis-radar-agent/redis-radar-agent --config /etc/redis-radar-agent/agent.yml --dry-run
```

## Deployment Script

Create a deployment script `deploy.sh`:

```bash
#!/bin/bash
set -e

BINARY_PATH="./redis-radar-agent"
CONFIG_PATH="./agent.yml"
SERVICE_NAME="redis-radar-agent"

echo "Deploying Redis Radar Agent..."

# Stop service if running
if sudo systemctl is-active --quiet $SERVICE_NAME; then
    echo "Stopping existing service..."
    sudo systemctl stop $SERVICE_NAME
fi

# Create directories
sudo mkdir -p /opt/$SERVICE_NAME
sudo mkdir -p /etc/$SERVICE_NAME
sudo mkdir -p /var/log/$SERVICE_NAME

# Install binary and config
echo "Installing binary and configuration..."
sudo cp $BINARY_PATH /opt/$SERVICE_NAME/
sudo cp $CONFIG_PATH /etc/$SERVICE_NAME/agent.yml

# Set permissions
sudo chown -R root:root /opt/$SERVICE_NAME
sudo chmod 755 /opt/$SERVICE_NAME/$SERVICE_NAME
sudo chown -R root:root /etc/$SERVICE_NAME
sudo chmod 644 /etc/$SERVICE_NAME/agent.yml
sudo chown -R nobody:nogroup /var/log/$SERVICE_NAME

# Create systemd service (service file content would be here)
echo "Creating systemd service..."
# ... (systemd service creation)

# Enable and start service
echo "Starting service..."
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

echo "Deployment complete!"
echo "Check status with: sudo systemctl status $SERVICE_NAME"
echo "View logs with: sudo journalctl -u $SERVICE_NAME -f"
```

## Troubleshooting

### Service Won't Start
```bash
# Check service status for errors
sudo systemctl status redis-radar-agent.service

# Check systemd journal for detailed errors
sudo journalctl -u redis-radar-agent.service -n 50

# Verify binary permissions and paths
ls -la /opt/redis-radar-agent/
ls -la /etc/redis-radar-agent/
```

### Permission Issues
```bash
# Check if user 'nobody' can access required files
sudo -u nobody ls -la /opt/redis-radar-agent/
sudo -u nobody ls -la /etc/redis-radar-agent/
```

### SELinux Troubleshooting (RHEL/CentOS/Fedora)
```bash
# Check SELinux status
sestatus

# Check for SELinux denials
sudo ausearch -m avc -ts recent

# If SELinux is blocking the service, create a custom policy
sudo ausearch -m avc -ts recent | audit2allow -M redis-radar-agent
sudo semodule -i redis-radar-agent.pp

# Alternative: Set SELinux to permissive mode for testing
sudo setenforce 0
```

### Log Issues
```bash
# Check log directory permissions
ls -la /var/log/redis-radar-agent/

# Test log rotation
sudo logrotate -f /etc/logrotate.d/redis-radar-agent
```

## Security Considerations

- The service runs as the `nobody` user with minimal privileges
- File system access is restricted using systemd security features
- Configuration files are owned by root and readable by the service user
- Logs are properly rotated to prevent disk space issues
- Network access is controlled through the systemd service configuration
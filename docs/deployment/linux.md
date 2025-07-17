# Redis Radar Agent Deployment Guide for Linux

This guide covers deployment methods for the `radar-agent` binary on Linux systems with systemd (Ubuntu 18.04+, RHEL/CentOS 7+, Fedora, etc.).

## Prerequisites

- Built `radar-agent` binary
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
  sudo semanage fcontext -a -t admin_home_t "/var/log/radar-agent(/.*)?"
  sudo restorecon -R /var/log/radar-agent
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
nohup ./radar-agent --config ./radar-agent.yml > /var/log/radar-agent/radar-agent.log 2>&1 &

# Check if running
ps aux | grep radar-agent

# View logs
tail -f redis-radar.log

# Stop the process
pkill radar-agent
```

To run with a specific config file location:

```bash
nohup ./radar-agent --config /path/to/your/radar-agent.yml > /var/log/radar-agent/radar-agent.log 2>&1 &
```

## Production Deployment with systemd

### 1. Create Directory Structure

```bash
# Create application directory
sudo mkdir -p /opt/radar-agent

# Create configuration directory
sudo mkdir -p /etc/radar-agent

# Create log directory
sudo mkdir -p /var/log/radar-agent
```

### 2. Install Files

```bash
# Copy binary to application directory
sudo cp ./radar-agent /opt/radar-agent/

# Copy configuration to system config directory
sudo cp ./radar-agent.yml /etc/radar-agent/

# Set appropriate permissions
sudo chown -R root:root /opt/radar-agent
sudo chmod 755 /opt/radar-agent/radar-agent
sudo chown -R root:root /etc/radar-agent
sudo chmod 644 /etc/radar-agent/radar-agent.yml
```

### 3. Create systemd Service

Create the service file at `/etc/systemd/system/radar-agent.service`:

```ini
[Unit]
Description=Redis Radar Agent
Documentation=https://github.com/your-org/radar-agent
After=network.target
Wants=network.target

[Service]
Type=simple
User=nobody
Group=nogroup
WorkingDirectory=/opt/radar-agent
ExecStart=/opt/radar-agent/radar-agent --config /etc/radar-agent/radar-agent.yml
Restart=always
RestartSec=10
TimeoutStartSec=30
TimeoutStopSec=30

# Logging
StandardOutput=append:/var/log/radar-agent/radar-agent.log
StandardError=append:/var/log/radar-agent/radar-agent.log

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/radar-agent

[Install]
WantedBy=multi-user.target
```

### 4. Configure Log Rotation

Create log rotation configuration at `/etc/logrotate.d/radar-agent`:

```
/var/log/radar-agent/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 nobody nogroup
    postrotate
        /bin/systemctl reload radar-agent.service > /dev/null 2>&1 || true
    endscript
}
```

### 5. Enable and Start Service

```bash
# Set correct permissions for log directory
sudo chown -R nobody:nogroup /var/log/radar-agent

# Reload systemd configuration
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable radar-agent.service

# Start the service
sudo systemctl start radar-agent.service

# Check service status
sudo systemctl status radar-agent.service
```

## Service Management

### Check Service Status
```bash
sudo systemctl status radar-agent.service
```

### View Logs
```bash
# Follow live logs
sudo journalctl -u radar-agent.service -f

# View recent logs
sudo journalctl -u radar-agent.service -n 100

# View logs since specific time
sudo journalctl -u radar-agent.service --since "2024-01-01 00:00:00"

# View application logs directly
sudo tail -f /var/log/radar-agent/radar-agent.log
```

### Restart Service
```bash
sudo systemctl restart radar-agent.service
```

### Stop Service
```bash
sudo systemctl stop radar-agent.service
```

### Disable Service
```bash
sudo systemctl disable radar-agent.service
```

## Configuration Management

### Update Configuration
```bash
# Edit configuration
sudo nano /etc/radar-agent/radar-agent.yml

# Restart service to apply changes
sudo systemctl restart radar-agent.service
```

### Validate Configuration
```bash
# Test configuration before applying
/opt/radar-agent/radar-agent --config /etc/radar-agent/radar-agent.yml --dry-run
```

## Deployment Script

Create a deployment script `deploy.sh`:

```bash
#!/bin/bash
set -e

BINARY_PATH="./radar-agent"
CONFIG_PATH="./radar-agent.yml"
SERVICE_NAME="radar-agent"

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
sudo cp $CONFIG_PATH /etc/$SERVICE_NAME/radar-agent.yml

# Set permissions
sudo chown -R root:root /opt/$SERVICE_NAME
sudo chmod 755 /opt/$SERVICE_NAME/$SERVICE_NAME
sudo chown -R root:root /etc/$SERVICE_NAME
sudo chmod 644 /etc/$SERVICE_NAME/radar-agent.yml
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
sudo systemctl status radar-agent.service

# Check systemd journal for detailed errors
sudo journalctl -u radar-agent.service -n 50

# Verify binary permissions and paths
ls -la /opt/radar-agent/
ls -la /etc/radar-agent/
```

### Permission Issues
```bash
# Check if user 'nobody' can access required files
sudo -u nobody ls -la /opt/radar-agent/
sudo -u nobody ls -la /etc/radar-agent/
```

### SELinux Troubleshooting (RHEL/CentOS/Fedora)
```bash
# Check SELinux status
sestatus

# Check for SELinux denials
sudo ausearch -m avc -ts recent

# If SELinux is blocking the service, create a custom policy
sudo ausearch -m avc -ts recent | audit2allow -M radar-agent
sudo semodule -i radar-agent.pp

# Alternative: Set SELinux to permissive mode for testing
sudo setenforce 0
```

### Log Issues
```bash
# Check log directory permissions
ls -la /var/log/radar-agent/

# Test log rotation
sudo logrotate -f /etc/logrotate.d/radar-agent
```

## Security Considerations

- The service runs as the `nobody` user with minimal privileges
- File system access is restricted using systemd security features
- Configuration files are owned by root and readable by the service user
- Logs are properly rotated to prevent disk space issues
- Network access is controlled through the systemd service configuration
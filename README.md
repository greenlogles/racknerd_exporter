# RackNerd Prometheus Exporter

A Prometheus exporter for RackNerd VPS control panel metrics.

## Features

Exports the following metrics for each VM:

- **VM Information**: hostname, IP address, OS, virtualization type (KVM/OpenVZ)
- **VM State**: Online/Offline/Unknown status
- **Bandwidth Usage**: Total allocation, used bandwidth, and usage percentage
- **Disk Usage**: Total space, used space, and usage percentage
- **Memory Usage**: Total memory, used memory, and usage percentage (when available)
- **VSwap Usage**: Total vswap, used vswap, and usage percentage (for OpenVZ VMs)

## Quick Start with Docker

Pull and run the pre-built image using environment variables:

```bash
docker run -d \
  --name racknerd-exporter \
  -p 9100:9100 \
  -e RACKNERD_USERNAME=your_username \
  -e RACKNERD_PASSWORD=your_password \
  ghcr.io/greenlogles/racknerd_exporter:latest
```

Or using command-line arguments:

```bash
docker run -d \
  --name racknerd-exporter \
  -p 9100:9100 \
  ghcr.io/greenlogles/racknerd_exporter:latest \
  --url https://nerdvm.racknerd.com \
  --username your_username \
  --password your_password
```

Then access metrics at `http://localhost:9100/metrics`

## Installation

### Prerequisites

- Python 3.7 or higher (for local installation)
- Docker (for containerized deployment)
- Access to RackNerd control panel

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Usage

### Command Line

```bash
python racknerd_exporter.py \
  --url https://nerdvm.racknerd.com \
  --username your_username \
  --password your_password \
  --port 9100
```

### Command Line Arguments

- `--url`: RackNerd control panel URL (required)
- `--username`: Your RackNerd username (required)
- `--password`: Your RackNerd password (required)
- `--port`: Port to expose metrics on (default: 9100)
- `--log-level`: Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)

### Using Environment Variables

For better security, you can pass credentials via environment variables:

```bash
export RACKNERD_URL="https://nerdvm.racknerd.com"
export RACKNERD_USERNAME="your_username"
export RACKNERD_PASSWORD="your_password"

python racknerd_exporter.py \
  --url "$RACKNERD_URL" \
  --username "$RACKNERD_USERNAME" \
  --password "$RACKNERD_PASSWORD"
```

## Metrics

### Available Metrics

| Metric Name | Type | Description | Labels |
|-------------|------|-------------|--------|
| `racknerd_vm_info` | Gauge | VM information (always 1) | hostname, ip_address, os, vm_type |
| `racknerd_vm_state` | Gauge | VM power state (1=online/running, 0=offline/stopped) | hostname |
| `racknerd_vm_stats_available` | Gauge | Whether VM stats are retrievable (1=available, 0=unavailable) | hostname |
| `racknerd_bandwidth_total_bytes` | Gauge | Total bandwidth allocation | hostname |
| `racknerd_bandwidth_used_bytes` | Gauge | Used bandwidth | hostname |
| `racknerd_bandwidth_usage_percent` | Gauge | Bandwidth usage percentage | hostname |
| `racknerd_disk_total_bytes` | Gauge | Total disk space | hostname |
| `racknerd_disk_used_bytes` | Gauge | Used disk space | hostname |
| `racknerd_disk_usage_percent` | Gauge | Disk usage percentage | hostname |
| `racknerd_memory_total_bytes` | Gauge | Total memory | hostname |
| `racknerd_memory_used_bytes` | Gauge | Used memory | hostname |
| `racknerd_memory_usage_percent` | Gauge | Memory usage percentage | hostname |
| `racknerd_vswap_total_bytes` | Gauge | Total vswap | hostname |
| `racknerd_vswap_used_bytes` | Gauge | Used vswap | hostname |
| `racknerd_vswap_usage_percent` | Gauge | VSwap usage percentage | hostname |

### Example Metrics Output

```
# HELP racknerd_vm_info Information about the VM
# TYPE racknerd_vm_info gauge
racknerd_vm_info{hostname="racknerd-1234567",ip_address="xxx.xxx.xxx.xxx",os="Debian 12 64 bit",vm_type="kvm"} 1.0

# HELP racknerd_vm_state VM power state (1=online, 0=offline)
# TYPE racknerd_vm_state gauge
racknerd_vm_state{hostname="racknerd-1234567"} 1.0

# HELP racknerd_vm_stats_available Whether VM stats are available (1=available, 0=unavailable)
# TYPE racknerd_vm_stats_available gauge
racknerd_vm_stats_available{hostname="racknerd-1234567"} 1.0

# HELP racknerd_bandwidth_total_bytes Total bandwidth allocation in bytes
# TYPE racknerd_bandwidth_total_bytes gauge
racknerd_bandwidth_total_bytes{hostname="racknerd-1234567"} 8589934592000.0

# HELP racknerd_bandwidth_used_bytes Used bandwidth in bytes
# TYPE racknerd_bandwidth_used_bytes gauge
racknerd_bandwidth_used_bytes{hostname="racknerd-1234567"} 899186688.0

# HELP racknerd_disk_total_bytes Total disk space in bytes
# TYPE racknerd_disk_total_bytes gauge
racknerd_disk_total_bytes{hostname="racknerd-1234567"} 32212254720.0

# HELP racknerd_disk_used_bytes Used disk space in bytes
# TYPE racknerd_disk_used_bytes gauge
racknerd_disk_used_bytes{hostname="racknerd-1234567"} 21876924416.0

# HELP racknerd_disk_usage_percent Disk usage percentage
# TYPE racknerd_disk_usage_percent gauge
racknerd_disk_usage_percent{hostname="racknerd-1234567"} 68.0
```

## Prometheus Configuration

Add the following to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'racknerd'
    static_configs:
      - targets: ['localhost:9100']
    scrape_interval: 600s  # Adjust as needed
```

## Running as a Service

### Systemd Service (Linux)

Create `/etc/systemd/system/racknerd-exporter.service`:

```ini
[Unit]
Description=RackNerd Prometheus Exporter
After=network.target

[Service]
Type=simple
User=prometheus
WorkingDirectory=/opt/racknerd_exporter
Environment="RACKNERD_URL=https://nerdvm.racknerd.com"
Environment="RACKNERD_USERNAME=your_username"
Environment="RACKNERD_PASSWORD=your_password"
ExecStart=/usr/bin/python3 /opt/racknerd_exporter/racknerd_exporter.py \
  --url ${RACKNERD_URL} \
  --username ${RACKNERD_USERNAME} \
  --password ${RACKNERD_PASSWORD} \
  --port 9100
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable racknerd-exporter
sudo systemctl start racknerd-exporter
sudo systemctl status racknerd-exporter
```

## Docker

### Using Pre-built Image from GitHub Container Registry

The easiest way to run the exporter is using the pre-built image with environment variables:

```bash
docker run -d \
  --name racknerd-exporter \
  -p 9100:9100 \
  -e RACKNERD_USERNAME=your_username \
  -e RACKNERD_PASSWORD=your_password \
  ghcr.io/greenlogles/racknerd_exporter:latest
```

Available environment variables:
- `RACKNERD_URL` - Control panel URL (default: `https://nerdvm.racknerd.com`)
- `RACKNERD_USERNAME` - Your username (required)
- `RACKNERD_PASSWORD` - Your password (required)
- `RACKNERD_PORT` - Exporter port (default: `9100`)
- `LOG_LEVEL` - Logging level: DEBUG, INFO, WARNING, ERROR (default: `INFO`)

### Build Docker Image Locally

```bash
docker build -t racknerd-exporter .
```

### Run with Docker

```bash
docker run -d \
  --name racknerd-exporter \
  -p 9100:9100 \
  racknerd-exporter \
  --url https://nerdvm.racknerd.com \
  --username your_username \
  --password your_password
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  racknerd-exporter:
    image: ghcr.io/greenlogles/racknerd_exporter:latest
    container_name: racknerd-exporter
    ports:
      - "9100:9100"
    environment:
      - RACKNERD_URL=${RACKNERD_URL:-https://nerdvm.racknerd.com}
      - RACKNERD_USERNAME=${RACKNERD_USERNAME}
      - RACKNERD_PASSWORD=${RACKNERD_PASSWORD}
      - RACKNERD_PORT=9100
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    restart: unless-stopped
```

Create a `.env` file:

```bash
RACKNERD_USERNAME=your_username
RACKNERD_PASSWORD=your_password
# Optional overrides:
# RACKNERD_URL=https://nerdvm.racknerd.com
# LOG_LEVEL=DEBUG
```

Run with:

```bash
docker-compose up -d
```

## Grafana Dashboard

Example PromQL queries for Grafana:

### Bandwidth Usage
```promql
racknerd_bandwidth_usage_percent{hostname="racknerd-1234567"}
```

### Disk Usage
```promql
racknerd_disk_usage_percent
```

### Memory Usage
```promql
100 * (racknerd_memory_used_bytes / racknerd_memory_total_bytes)
```

### VMs Online Count
```promql
count(racknerd_vm_state == 1)
```

### VMs Offline
```promql
racknerd_vm_state == 0
```

### Check VM Power State
```promql
# Get state for specific VM
racknerd_vm_state{hostname="racknerd-1234567"}

# Alert when VM goes offline
racknerd_vm_state == 0
```

## Example Prometheus Alerts

Add to your Prometheus `alerts.yml`:

```yaml
groups:
  - name: racknerd
    interval: 300s
    rules:
      # Alert when VM goes offline
      - alert: RackNerdVMDown
        expr: racknerd_vm_state == 0
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "RackNerd VM {{ $labels.hostname }} is offline"
          description: "VM {{ $labels.hostname }} ({{ $labels.vm_id }}) has been offline for more than 5 minutes."

      # Alert when stats are unavailable
      - alert: RackNerdStatsUnavailable
        expr: racknerd_vm_stats_available == 0
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Cannot fetch stats for {{ $labels.hostname }}"
          description: "Stats have been unavailable for VM {{ $labels.hostname }} for more than 10 minutes."

      # Alert on high disk usage
      - alert: RackNerdHighDiskUsage
        expr: racknerd_disk_usage_percent > 85
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "High disk usage on {{ $labels.hostname }}"
          description: "Disk usage is {{ $value }}% on VM {{ $labels.hostname }}."

      # Alert on high bandwidth usage
      - alert: RackNerdHighBandwidthUsage
        expr: racknerd_bandwidth_usage_percent > 80
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "High bandwidth usage on {{ $labels.hostname }}"
          description: "Bandwidth usage is {{ $value }}% on VM {{ $labels.hostname }}."

      # Alert on high memory usage (when available)
      - alert: RackNerdHighMemoryUsage
        expr: racknerd_memory_usage_percent > 90
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage on {{ $labels.hostname }}"
          description: "Memory usage is {{ $value }}% on VM {{ $labels.hostname }}."
```

## Troubleshooting

### Authentication Issues

If you get authentication errors:
1. Verify your credentials are correct
2. Try logging in manually to the web interface
3. Check if there are any CAPTCHA or 2FA requirements

### No Metrics Appearing

1. Check the exporter logs: `--log-level DEBUG`
2. Verify the exporter is running: `curl http://localhost:9100/metrics`
3. Check Prometheus is scraping: Look in Prometheus targets page

### SSL/TLS Errors

If you encounter SSL certificate errors, you may need to update your CA certificates or disable SSL verification (not recommended for production).

## Security Considerations

- **Credentials**: Never commit credentials to version control
- **Network**: Run the exporter in a secure network
- **Firewall**: Restrict access to the metrics port
- **HTTPS**: Consider using a reverse proxy with HTTPS

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

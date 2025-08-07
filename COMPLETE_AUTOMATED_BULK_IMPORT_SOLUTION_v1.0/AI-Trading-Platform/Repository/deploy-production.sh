#!/bin/bash

# Bio-Quantum AI Trading Platform - Production Deployment Script
# Version: 1.0
# Description: Complete production deployment with security hardening

set -euo pipefail

# Configuration
DEPLOYMENT_ENV="production"
PROJECT_ROOT="/opt/bio-quantum-ai"
BACKUP_DIR="/opt/bio-quantum-ai/backups"
LOG_DIR="/var/log/bio-quantum-ai"
SERVICE_USER="bio-quantum"
DB_NAME="bio_quantum_prod"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root for security reasons"
        exit 1
    fi
}

# Pre-deployment checks
pre_deployment_checks() {
    log "Running pre-deployment checks..."
    
    # Check system requirements
    if ! command -v python3.11 &> /dev/null; then
        error "Python 3.11 is required but not installed"
        exit 1
    fi
    
    if ! command -v redis-server &> /dev/null; then
        error "Redis is required but not installed"
        exit 1
    fi
    
    if ! command -v postgresql &> /dev/null; then
        error "PostgreSQL is required but not installed"
        exit 1
    fi
    
    # Check disk space (minimum 10GB)
    available_space=$(df / | awk 'NR==2 {print $4}')
    if [[ $available_space -lt 10485760 ]]; then
        error "Insufficient disk space. At least 10GB required"
        exit 1
    fi
    
    # Check memory (minimum 8GB)
    total_memory=$(free -m | awk 'NR==2{print $2}')
    if [[ $total_memory -lt 8192 ]]; then
        warning "Less than 8GB RAM detected. Performance may be impacted"
    fi
    
    success "Pre-deployment checks passed"
}

# Create system user and directories
setup_system() {
    log "Setting up system user and directories..."
    
    # Create service user if it doesn't exist
    if ! id "$SERVICE_USER" &>/dev/null; then
        sudo useradd -r -s /bin/false -d "$PROJECT_ROOT" "$SERVICE_USER"
        success "Created service user: $SERVICE_USER"
    fi
    
    # Create directories
    sudo mkdir -p "$PROJECT_ROOT"/{app,config,logs,data,backups}
    sudo mkdir -p "$LOG_DIR"
    sudo mkdir -p "$BACKUP_DIR"
    
    # Set permissions
    sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$PROJECT_ROOT"
    sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$LOG_DIR"
    sudo chmod 750 "$PROJECT_ROOT"
    sudo chmod 755 "$LOG_DIR"
    
    success "System setup completed"
}

# Install Python dependencies
install_dependencies() {
    log "Installing Python dependencies..."
    
    # Create virtual environment
    sudo -u "$SERVICE_USER" python3.11 -m venv "$PROJECT_ROOT/venv"
    
    # Activate virtual environment and install dependencies
    sudo -u "$SERVICE_USER" bash -c "
        source $PROJECT_ROOT/venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
    "
    
    success "Dependencies installed"
}

# Deploy application code
deploy_application() {
    log "Deploying application code..."
    
    # Create backup of existing deployment
    if [[ -d "$PROJECT_ROOT/app" ]]; then
        timestamp=$(date +%Y%m%d_%H%M%S)
        sudo -u "$SERVICE_USER" cp -r "$PROJECT_ROOT/app" "$BACKUP_DIR/app_backup_$timestamp"
        success "Created backup: app_backup_$timestamp"
    fi
    
    # Copy application files
    sudo -u "$SERVICE_USER" cp -r ../trading-api-integration "$PROJECT_ROOT/app/"
    sudo -u "$SERVICE_USER" cp -r ../trade-execution-engine "$PROJECT_ROOT/app/"
    sudo -u "$SERVICE_USER" cp -r ../knowledge-nugget-loop "$PROJECT_ROOT/app/"
    sudo -u "$SERVICE_USER" cp -r ../live-strategy-execution "$PROJECT_ROOT/app/"
    sudo -u "$SERVICE_USER" cp -r ../cicd-pipeline "$PROJECT_ROOT/app/"
    
    # Set proper permissions
    sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$PROJECT_ROOT/app"
    sudo find "$PROJECT_ROOT/app" -type f -name "*.py" -exec chmod 644 {} \;
    sudo find "$PROJECT_ROOT/app" -type d -exec chmod 755 {} \;
    
    success "Application code deployed"
}

# Configure database
setup_database() {
    log "Setting up database..."
    
    # Create database and user
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || true
    sudo -u postgres psql -c "CREATE USER $SERVICE_USER WITH PASSWORD 'secure_password_here';" 2>/dev/null || true
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $SERVICE_USER;" 2>/dev/null || true
    
    # Run database migrations
    sudo -u "$SERVICE_USER" bash -c "
        source $PROJECT_ROOT/venv/bin/activate
        cd $PROJECT_ROOT/app
        python manage.py migrate
    "
    
    success "Database setup completed"
}

# Configure Redis
setup_redis() {
    log "Configuring Redis..."
    
    # Create Redis configuration
    sudo tee /etc/redis/redis-bio-quantum.conf > /dev/null <<EOF
# Bio-Quantum AI Redis Configuration
port 6380
bind 127.0.0.1
protected-mode yes
requirepass secure_redis_password_here
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
dir /var/lib/redis-bio-quantum
logfile /var/log/redis/redis-bio-quantum.log
EOF
    
    # Create Redis data directory
    sudo mkdir -p /var/lib/redis-bio-quantum
    sudo chown redis:redis /var/lib/redis-bio-quantum
    sudo chmod 750 /var/lib/redis-bio-quantum
    
    # Start Redis service
    sudo systemctl enable redis-server@bio-quantum
    sudo systemctl start redis-server@bio-quantum
    
    success "Redis configuration completed"
}

# Configure SSL/TLS certificates
setup_ssl() {
    log "Setting up SSL/TLS certificates..."
    
    # Create SSL directory
    sudo mkdir -p "$PROJECT_ROOT/ssl"
    
    # Generate self-signed certificate for development
    # In production, use proper certificates from Let's Encrypt or CA
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
        -keyout "$PROJECT_ROOT/ssl/bio-quantum.key" \
        -out "$PROJECT_ROOT/ssl/bio-quantum.crt" \
        -subj "/C=US/ST=State/L=City/O=Bio-Quantum-AI/CN=bio-quantum.local"
    
    # Set proper permissions
    sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$PROJECT_ROOT/ssl"
    sudo chmod 600 "$PROJECT_ROOT/ssl/bio-quantum.key"
    sudo chmod 644 "$PROJECT_ROOT/ssl/bio-quantum.crt"
    
    success "SSL certificates configured"
}

# Create systemd services
create_services() {
    log "Creating systemd services..."
    
    # Trading API Service
    sudo tee /etc/systemd/system/bio-quantum-api.service > /dev/null <<EOF
[Unit]
Description=Bio-Quantum AI Trading API
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=exec
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$PROJECT_ROOT/app
Environment=PATH=$PROJECT_ROOT/venv/bin
Environment=PYTHONPATH=$PROJECT_ROOT/app
ExecStart=$PROJECT_ROOT/venv/bin/python -m trading_api_integration.main
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=bio-quantum-api

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$PROJECT_ROOT $LOG_DIR

[Install]
WantedBy=multi-user.target
EOF

    # Execution Engine Service
    sudo tee /etc/systemd/system/bio-quantum-execution.service > /dev/null <<EOF
[Unit]
Description=Bio-Quantum AI Execution Engine
After=network.target bio-quantum-api.service
Requires=bio-quantum-api.service

[Service]
Type=exec
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$PROJECT_ROOT/app
Environment=PATH=$PROJECT_ROOT/venv/bin
Environment=PYTHONPATH=$PROJECT_ROOT/app
ExecStart=$PROJECT_ROOT/venv/bin/python -m trade_execution_engine.main
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=bio-quantum-execution

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$PROJECT_ROOT $LOG_DIR

[Install]
WantedBy=multi-user.target
EOF

    # Knowledge Loop Service
    sudo tee /etc/systemd/system/bio-quantum-knowledge.service > /dev/null <<EOF
[Unit]
Description=Bio-Quantum AI Knowledge Loop
After=network.target bio-quantum-execution.service
Requires=bio-quantum-execution.service

[Service]
Type=exec
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$PROJECT_ROOT/app
Environment=PATH=$PROJECT_ROOT/venv/bin
Environment=PYTHONPATH=$PROJECT_ROOT/app
ExecStart=$PROJECT_ROOT/venv/bin/python -m knowledge_nugget_loop.main
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=bio-quantum-knowledge

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$PROJECT_ROOT $LOG_DIR

[Install]
WantedBy=multi-user.target
EOF

    # Live Execution Manager Service
    sudo tee /etc/systemd/system/bio-quantum-manager.service > /dev/null <<EOF
[Unit]
Description=Bio-Quantum AI Live Execution Manager
After=network.target bio-quantum-knowledge.service
Requires=bio-quantum-knowledge.service

[Service]
Type=exec
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$PROJECT_ROOT/app
Environment=PATH=$PROJECT_ROOT/venv/bin
Environment=PYTHONPATH=$PROJECT_ROOT/app
ExecStart=$PROJECT_ROOT/venv/bin/python -m live_strategy_execution.main
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=bio-quantum-manager

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$PROJECT_ROOT $LOG_DIR

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd
    sudo systemctl daemon-reload
    
    success "Systemd services created"
}

# Configure monitoring
setup_monitoring() {
    log "Setting up monitoring..."
    
    # Create monitoring configuration
    sudo -u "$SERVICE_USER" tee "$PROJECT_ROOT/config/monitoring.yml" > /dev/null <<EOF
monitoring:
  enabled: true
  metrics_port: 9090
  health_check_interval: 30
  alert_thresholds:
    cpu_usage: 80
    memory_usage: 85
    disk_usage: 90
    response_time_ms: 1000
  
  alerts:
    email:
      enabled: true
      smtp_server: "smtp.gmail.com"
      smtp_port: 587
      username: "alerts@bio-quantum.ai"
      recipients:
        - "admin@bio-quantum.ai"
        - "ops@bio-quantum.ai"
    
    slack:
      enabled: true
      webhook_url: "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
      channel: "#bio-quantum-alerts"

  dashboards:
    grafana:
      enabled: true
      port: 3000
      admin_password: "secure_grafana_password"
    
    prometheus:
      enabled: true
      port: 9090
      retention: "30d"
EOF

    success "Monitoring configuration completed"
}

# Configure firewall
setup_firewall() {
    log "Configuring firewall..."
    
    # Enable UFW if not already enabled
    sudo ufw --force enable
    
    # Default policies
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    
    # Allow SSH (adjust port as needed)
    sudo ufw allow 22/tcp
    
    # Allow HTTPS
    sudo ufw allow 443/tcp
    
    # Allow monitoring ports (restrict to specific IPs in production)
    sudo ufw allow from 10.0.0.0/8 to any port 9090
    sudo ufw allow from 10.0.0.0/8 to any port 3000
    
    # Allow database connections (restrict to application servers)
    sudo ufw allow from 127.0.0.1 to any port 5432
    sudo ufw allow from 127.0.0.1 to any port 6380
    
    success "Firewall configured"
}

# Security hardening
security_hardening() {
    log "Applying security hardening..."
    
    # Set file permissions
    sudo find "$PROJECT_ROOT" -type f -name "*.py" -exec chmod 644 {} \;
    sudo find "$PROJECT_ROOT" -type d -exec chmod 755 {} \;
    sudo chmod 600 "$PROJECT_ROOT/config"/*.yml
    sudo chmod 600 "$PROJECT_ROOT/ssl"/*.key
    
    # Create security configuration
    sudo -u "$SERVICE_USER" tee "$PROJECT_ROOT/config/security.yml" > /dev/null <<EOF
security:
  encryption:
    algorithm: "AES-256-GCM"
    key_derivation: "PBKDF2"
    iterations: 100000
    salt_length: 32
  
  api_security:
    rate_limiting:
      enabled: true
      requests_per_minute: 60
      burst_size: 10
    
    authentication:
      jwt_secret: "$(openssl rand -base64 64)"
      token_expiry: 3600
      refresh_token_expiry: 86400
    
    cors:
      enabled: true
      allowed_origins:
        - "https://bio-quantum.ai"
        - "https://app.bio-quantum.ai"
  
  database_security:
    ssl_mode: "require"
    connection_timeout: 30
    max_connections: 20
  
  logging:
    level: "INFO"
    sensitive_data_masking: true
    audit_trail: true
    log_rotation:
      max_size: "100MB"
      max_files: 10
EOF

    success "Security hardening completed"
}

# Start services
start_services() {
    log "Starting services..."
    
    # Enable and start services in order
    services=("bio-quantum-api" "bio-quantum-execution" "bio-quantum-knowledge" "bio-quantum-manager")
    
    for service in "${services[@]}"; do
        sudo systemctl enable "$service"
        sudo systemctl start "$service"
        
        # Wait for service to start
        sleep 5
        
        if sudo systemctl is-active --quiet "$service"; then
            success "Started $service"
        else
            error "Failed to start $service"
            sudo journalctl -u "$service" --no-pager -n 20
            exit 1
        fi
    done
    
    success "All services started successfully"
}

# Health check
health_check() {
    log "Running health checks..."
    
    # Check service status
    services=("bio-quantum-api" "bio-quantum-execution" "bio-quantum-knowledge" "bio-quantum-manager")
    
    for service in "${services[@]}"; do
        if sudo systemctl is-active --quiet "$service"; then
            success "$service is running"
        else
            error "$service is not running"
            return 1
        fi
    done
    
    # Check database connectivity
    if sudo -u "$SERVICE_USER" psql -d "$DB_NAME" -c "SELECT 1;" &>/dev/null; then
        success "Database connectivity OK"
    else
        error "Database connectivity failed"
        return 1
    fi
    
    # Check Redis connectivity
    if redis-cli -p 6380 -a "secure_redis_password_here" ping &>/dev/null; then
        success "Redis connectivity OK"
    else
        error "Redis connectivity failed"
        return 1
    fi
    
    success "All health checks passed"
}

# Create deployment summary
create_summary() {
    log "Creating deployment summary..."
    
    sudo -u "$SERVICE_USER" tee "$PROJECT_ROOT/DEPLOYMENT_SUMMARY.md" > /dev/null <<EOF
# Bio-Quantum AI Trading Platform - Deployment Summary

## Deployment Information
- **Date:** $(date)
- **Environment:** $DEPLOYMENT_ENV
- **Version:** 1.0.0
- **Deployed by:** $(whoami)

## Service Status
$(sudo systemctl status bio-quantum-api bio-quantum-execution bio-quantum-knowledge bio-quantum-manager --no-pager -l)

## Configuration Files
- Application: $PROJECT_ROOT/config/
- SSL Certificates: $PROJECT_ROOT/ssl/
- Logs: $LOG_DIR/
- Backups: $BACKUP_DIR/

## Service Management
\`\`\`bash
# Start all services
sudo systemctl start bio-quantum-api bio-quantum-execution bio-quantum-knowledge bio-quantum-manager

# Stop all services
sudo systemctl stop bio-quantum-manager bio-quantum-knowledge bio-quantum-execution bio-quantum-api

# Check service status
sudo systemctl status bio-quantum-*

# View logs
sudo journalctl -u bio-quantum-api -f
\`\`\`

## Security Notes
- All services run as non-root user: $SERVICE_USER
- SSL/TLS encryption enabled
- Firewall configured with minimal required ports
- Database and Redis secured with authentication
- Sensitive configuration files have restricted permissions

## Monitoring
- Metrics available on port 9090
- Grafana dashboard on port 3000
- Health checks every 30 seconds
- Alerts configured for email and Slack

## Next Steps
1. Configure exchange API credentials
2. Set up monitoring dashboards
3. Configure backup schedules
4. Test with paper trading
5. Gradually increase live trading capital
EOF

    success "Deployment summary created"
}

# Main deployment function
main() {
    log "Starting Bio-Quantum AI Trading Platform deployment..."
    
    check_root
    pre_deployment_checks
    setup_system
    install_dependencies
    deploy_application
    setup_database
    setup_redis
    setup_ssl
    create_services
    setup_monitoring
    setup_firewall
    security_hardening
    start_services
    health_check
    create_summary
    
    success "🚀 Bio-Quantum AI Trading Platform deployed successfully!"
    success "📊 Access monitoring at: https://$(hostname):3000"
    success "📋 Deployment summary: $PROJECT_ROOT/DEPLOYMENT_SUMMARY.md"
    success "📝 Logs location: $LOG_DIR/"
    
    warning "⚠️  Remember to:"
    warning "   1. Configure exchange API credentials"
    warning "   2. Update SSL certificates for production"
    warning "   3. Set up proper backup schedules"
    warning "   4. Configure monitoring alerts"
    warning "   5. Test thoroughly before live trading"
}

# Run main function
main "$@"


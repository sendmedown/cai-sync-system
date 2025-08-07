#!/bin/bash

# Bio-Quantum AI Trading Platform - Health Check Script
# Version: 1.0
# Description: Comprehensive system health monitoring

set -euo pipefail

# Configuration
PROJECT_ROOT="/opt/bio-quantum-ai"
LOG_DIR="/var/log/bio-quantum-ai"
SERVICE_USER="bio-quantum"
HEALTH_CHECK_LOG="$LOG_DIR/health-check.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Health check results
OVERALL_STATUS="HEALTHY"
FAILED_CHECKS=()
WARNING_CHECKS=()

# Logging function
log() {
    local message="$1"
    local timestamp=$(date +'%Y-%m-%d %H:%M:%S')
    echo -e "${BLUE}[$timestamp]${NC} $message"
    echo "[$timestamp] $message" >> "$HEALTH_CHECK_LOG"
}

success() {
    local message="$1"
    echo -e "${GREEN}[✓]${NC} $message"
    echo "[SUCCESS] $message" >> "$HEALTH_CHECK_LOG"
}

warning() {
    local message="$1"
    echo -e "${YELLOW}[⚠]${NC} $message"
    echo "[WARNING] $message" >> "$HEALTH_CHECK_LOG"
    WARNING_CHECKS+=("$message")
    if [[ "$OVERALL_STATUS" == "HEALTHY" ]]; then
        OVERALL_STATUS="WARNING"
    fi
}

error() {
    local message="$1"
    echo -e "${RED}[✗]${NC} $message"
    echo "[ERROR] $message" >> "$HEALTH_CHECK_LOG"
    FAILED_CHECKS+=("$message")
    OVERALL_STATUS="CRITICAL"
}

# Check system resources
check_system_resources() {
    log "Checking system resources..."
    
    # Check CPU usage
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')
    if (( $(echo "$cpu_usage > 80" | bc -l) )); then
        warning "High CPU usage: ${cpu_usage}%"
    else
        success "CPU usage: ${cpu_usage}%"
    fi
    
    # Check memory usage
    memory_info=$(free | grep Mem)
    total_memory=$(echo $memory_info | awk '{print $2}')
    used_memory=$(echo $memory_info | awk '{print $3}')
    memory_usage=$(echo "scale=2; $used_memory * 100 / $total_memory" | bc)
    
    if (( $(echo "$memory_usage > 85" | bc -l) )); then
        warning "High memory usage: ${memory_usage}%"
    else
        success "Memory usage: ${memory_usage}%"
    fi
    
    # Check disk usage
    disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [[ $disk_usage -gt 90 ]]; then
        error "Critical disk usage: ${disk_usage}%"
    elif [[ $disk_usage -gt 80 ]]; then
        warning "High disk usage: ${disk_usage}%"
    else
        success "Disk usage: ${disk_usage}%"
    fi
    
    # Check load average
    load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    cpu_cores=$(nproc)
    load_threshold=$(echo "scale=2; $cpu_cores * 0.8" | bc)
    
    if (( $(echo "$load_avg > $load_threshold" | bc -l) )); then
        warning "High load average: $load_avg (threshold: $load_threshold)"
    else
        success "Load average: $load_avg"
    fi
}

# Check service status
check_services() {
    log "Checking service status..."
    
    services=("bio-quantum-api" "bio-quantum-execution" "bio-quantum-knowledge" "bio-quantum-manager")
    
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service"; then
            success "$service is running"
            
            # Check service memory usage
            pid=$(systemctl show --property MainPID --value "$service")
            if [[ "$pid" != "0" ]]; then
                memory_kb=$(ps -o rss= -p "$pid" 2>/dev/null || echo "0")
                memory_mb=$(echo "scale=2; $memory_kb / 1024" | bc)
                
                if (( $(echo "$memory_mb > 1024" | bc -l) )); then
                    warning "$service using high memory: ${memory_mb}MB"
                else
                    success "$service memory usage: ${memory_mb}MB"
                fi
            fi
        else
            error "$service is not running"
        fi
    done
}

# Check database connectivity
check_database() {
    log "Checking database connectivity..."
    
    # Check PostgreSQL service
    if systemctl is-active --quiet postgresql; then
        success "PostgreSQL service is running"
        
        # Test database connection
        if sudo -u "$SERVICE_USER" psql -d bio_quantum_prod -c "SELECT 1;" &>/dev/null; then
            success "Database connection successful"
            
            # Check database size
            db_size=$(sudo -u "$SERVICE_USER" psql -d bio_quantum_prod -t -c "SELECT pg_size_pretty(pg_database_size('bio_quantum_prod'));" | xargs)
            success "Database size: $db_size"
            
            # Check active connections
            active_connections=$(sudo -u "$SERVICE_USER" psql -d bio_quantum_prod -t -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';" | xargs)
            max_connections=$(sudo -u "$SERVICE_USER" psql -d bio_quantum_prod -t -c "SHOW max_connections;" | xargs)
            
            if [[ $active_connections -gt $((max_connections * 80 / 100)) ]]; then
                warning "High database connections: $active_connections/$max_connections"
            else
                success "Database connections: $active_connections/$max_connections"
            fi
            
        else
            error "Database connection failed"
        fi
    else
        error "PostgreSQL service is not running"
    fi
}

# Check Redis connectivity
check_redis() {
    log "Checking Redis connectivity..."
    
    # Check Redis service
    if systemctl is-active --quiet redis-server; then
        success "Redis service is running"
        
        # Test Redis connection
        if redis-cli -p 6380 ping &>/dev/null; then
            success "Redis connection successful"
            
            # Check Redis memory usage
            redis_memory=$(redis-cli -p 6380 info memory | grep used_memory_human | cut -d: -f2 | tr -d '\r')
            success "Redis memory usage: $redis_memory"
            
            # Check Redis connected clients
            connected_clients=$(redis-cli -p 6380 info clients | grep connected_clients | cut -d: -f2 | tr -d '\r')
            success "Redis connected clients: $connected_clients"
            
        else
            error "Redis connection failed"
        fi
    else
        error "Redis service is not running"
    fi
}

# Check exchange connectivity
check_exchanges() {
    log "Checking exchange connectivity..."
    
    # Check Binance API
    if curl -s --max-time 10 "https://api.binance.com/api/v3/ping" &>/dev/null; then
        success "Binance API connectivity OK"
        
        # Check API response time
        response_time=$(curl -s -w "%{time_total}" -o /dev/null "https://api.binance.com/api/v3/time")
        response_time_ms=$(echo "$response_time * 1000" | bc | cut -d. -f1)
        
        if [[ $response_time_ms -gt 1000 ]]; then
            warning "Binance API slow response: ${response_time_ms}ms"
        else
            success "Binance API response time: ${response_time_ms}ms"
        fi
    else
        error "Binance API connectivity failed"
    fi
    
    # Check Coinbase Pro API (if configured)
    if curl -s --max-time 10 "https://api.pro.coinbase.com/time" &>/dev/null; then
        success "Coinbase Pro API connectivity OK"
    else
        warning "Coinbase Pro API connectivity failed (may not be configured)"
    fi
}

# Check SSL certificates
check_ssl_certificates() {
    log "Checking SSL certificates..."
    
    cert_file="$PROJECT_ROOT/ssl/bio-quantum.crt"
    
    if [[ -f "$cert_file" ]]; then
        # Check certificate expiration
        expiry_date=$(openssl x509 -enddate -noout -in "$cert_file" | cut -d= -f2)
        expiry_timestamp=$(date -d "$expiry_date" +%s)
        current_timestamp=$(date +%s)
        days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))
        
        if [[ $days_until_expiry -lt 7 ]]; then
            error "SSL certificate expires in $days_until_expiry days"
        elif [[ $days_until_expiry -lt 30 ]]; then
            warning "SSL certificate expires in $days_until_expiry days"
        else
            success "SSL certificate valid for $days_until_expiry days"
        fi
    else
        error "SSL certificate file not found"
    fi
}

# Check log files
check_logs() {
    log "Checking log files..."
    
    # Check log directory
    if [[ -d "$LOG_DIR" ]]; then
        success "Log directory exists"
        
        # Check log file sizes
        for log_file in "$LOG_DIR"/*.log; do
            if [[ -f "$log_file" ]]; then
                file_size=$(du -h "$log_file" | cut -f1)
                file_size_mb=$(du -m "$log_file" | cut -f1)
                
                if [[ $file_size_mb -gt 100 ]]; then
                    warning "Large log file: $(basename "$log_file") ($file_size)"
                else
                    success "Log file size OK: $(basename "$log_file") ($file_size)"
                fi
            fi
        done
        
        # Check for recent errors in logs
        error_count=$(grep -c "ERROR" "$LOG_DIR"/*.log 2>/dev/null | awk -F: '{sum += $2} END {print sum+0}')
        if [[ $error_count -gt 10 ]]; then
            warning "High error count in logs: $error_count errors"
        else
            success "Error count in logs: $error_count errors"
        fi
    else
        error "Log directory not found"
    fi
}

# Check network connectivity
check_network() {
    log "Checking network connectivity..."
    
    # Check internet connectivity
    if ping -c 1 8.8.8.8 &>/dev/null; then
        success "Internet connectivity OK"
    else
        error "Internet connectivity failed"
    fi
    
    # Check DNS resolution
    if nslookup api.binance.com &>/dev/null; then
        success "DNS resolution OK"
    else
        error "DNS resolution failed"
    fi
    
    # Check port availability
    ports=(80 443 5432 6380)
    for port in "${ports[@]}"; do
        if netstat -tuln | grep ":$port " &>/dev/null; then
            success "Port $port is listening"
        else
            warning "Port $port is not listening"
        fi
    done
}

# Check application health endpoints
check_application_health() {
    log "Checking application health endpoints..."
    
    # Check main health endpoint
    if curl -s -k --max-time 10 "https://localhost/health" | grep -q "healthy"; then
        success "Main health endpoint OK"
    else
        error "Main health endpoint failed"
    fi
    
    # Check component health endpoints
    endpoints=("database" "redis" "exchanges")
    for endpoint in "${endpoints[@]}"; do
        if curl -s -k --max-time 10 "https://localhost/health/$endpoint" | grep -q "healthy"; then
            success "Health endpoint /$endpoint OK"
        else
            warning "Health endpoint /$endpoint failed"
        fi
    done
}

# Check backup status
check_backups() {
    log "Checking backup status..."
    
    backup_dir="$PROJECT_ROOT/backups"
    
    if [[ -d "$backup_dir" ]]; then
        success "Backup directory exists"
        
        # Check for recent database backup
        latest_db_backup=$(find "$backup_dir" -name "*.sql" -mtime -1 | head -1)
        if [[ -n "$latest_db_backup" ]]; then
            success "Recent database backup found: $(basename "$latest_db_backup")"
        else
            warning "No recent database backup found"
        fi
        
        # Check for recent application backup
        latest_app_backup=$(find "$backup_dir" -name "*.tar.gz" -mtime -1 | head -1)
        if [[ -n "$latest_app_backup" ]]; then
            success "Recent application backup found: $(basename "$latest_app_backup")"
        else
            warning "No recent application backup found"
        fi
        
        # Check backup directory size
        backup_size=$(du -sh "$backup_dir" | cut -f1)
        success "Backup directory size: $backup_size"
    else
        warning "Backup directory not found"
    fi
}

# Check security
check_security() {
    log "Checking security status..."
    
    # Check for failed login attempts
    failed_logins=$(grep "Failed password" /var/log/auth.log 2>/dev/null | wc -l || echo "0")
    if [[ $failed_logins -gt 10 ]]; then
        warning "High number of failed login attempts: $failed_logins"
    else
        success "Failed login attempts: $failed_logins"
    fi
    
    # Check firewall status
    if ufw status | grep -q "Status: active"; then
        success "Firewall is active"
    else
        warning "Firewall is not active"
    fi
    
    # Check for suspicious processes
    suspicious_processes=$(ps aux | grep -E "(bitcoin|mining|crypto)" | grep -v grep | wc -l)
    if [[ $suspicious_processes -gt 0 ]]; then
        warning "Suspicious processes detected: $suspicious_processes"
    else
        success "No suspicious processes detected"
    fi
}

# Generate health report
generate_report() {
    log "Generating health report..."
    
    report_file="$LOG_DIR/health-report-$(date +%Y%m%d_%H%M%S).json"
    
    cat > "$report_file" <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "overall_status": "$OVERALL_STATUS",
    "failed_checks": $(printf '%s\n' "${FAILED_CHECKS[@]}" | jq -R . | jq -s .),
    "warning_checks": $(printf '%s\n' "${WARNING_CHECKS[@]}" | jq -R . | jq -s .),
    "system_info": {
        "hostname": "$(hostname)",
        "uptime": "$(uptime -p)",
        "kernel": "$(uname -r)",
        "os": "$(lsb_release -d | cut -f2)"
    },
    "resource_usage": {
        "cpu_usage": "$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')%",
        "memory_usage": "$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')%",
        "disk_usage": "$(df / | awk 'NR==2 {print $5}')",
        "load_average": "$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')"
    }
}
EOF
    
    success "Health report generated: $report_file"
}

# Send alerts if needed
send_alerts() {
    if [[ "$OVERALL_STATUS" != "HEALTHY" ]]; then
        log "Sending alerts for $OVERALL_STATUS status..."
        
        # Send email alert (if configured)
        if command -v mail &> /dev/null; then
            {
                echo "Bio-Quantum AI Trading Platform Health Alert"
                echo "=========================================="
                echo ""
                echo "Status: $OVERALL_STATUS"
                echo "Timestamp: $(date)"
                echo "Hostname: $(hostname)"
                echo ""
                
                if [[ ${#FAILED_CHECKS[@]} -gt 0 ]]; then
                    echo "Failed Checks:"
                    printf '%s\n' "${FAILED_CHECKS[@]}"
                    echo ""
                fi
                
                if [[ ${#WARNING_CHECKS[@]} -gt 0 ]]; then
                    echo "Warning Checks:"
                    printf '%s\n' "${WARNING_CHECKS[@]}"
                    echo ""
                fi
                
                echo "Please check the system immediately."
            } | mail -s "Bio-Quantum AI Health Alert: $OVERALL_STATUS" admin@bio-quantum.ai
        fi
        
        # Send Slack alert (if webhook configured)
        if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
            curl -X POST -H 'Content-type: application/json' \
                --data "{\"text\":\"🚨 Bio-Quantum AI Health Alert: $OVERALL_STATUS on $(hostname)\"}" \
                "$SLACK_WEBHOOK_URL" &>/dev/null || true
        fi
    fi
}

# Main health check function
main() {
    log "Starting Bio-Quantum AI Trading Platform health check..."
    
    # Create log directory if it doesn't exist
    mkdir -p "$LOG_DIR"
    
    # Run all health checks
    check_system_resources
    check_services
    check_database
    check_redis
    check_exchanges
    check_ssl_certificates
    check_logs
    check_network
    check_application_health
    check_backups
    check_security
    
    # Generate report and send alerts
    generate_report
    send_alerts
    
    # Summary
    echo ""
    log "Health check completed"
    echo -e "Overall Status: ${GREEN}$OVERALL_STATUS${NC}"
    
    if [[ ${#FAILED_CHECKS[@]} -gt 0 ]]; then
        echo -e "${RED}Failed Checks (${#FAILED_CHECKS[@]}):${NC}"
        printf '%s\n' "${FAILED_CHECKS[@]}"
    fi
    
    if [[ ${#WARNING_CHECKS[@]} -gt 0 ]]; then
        echo -e "${YELLOW}Warning Checks (${#WARNING_CHECKS[@]}):${NC}"
        printf '%s\n' "${WARNING_CHECKS[@]}"
    fi
    
    # Exit with appropriate code
    case "$OVERALL_STATUS" in
        "HEALTHY")
            exit 0
            ;;
        "WARNING")
            exit 1
            ;;
        "CRITICAL")
            exit 2
            ;;
    esac
}

# Run main function
main "$@"


#!/bin/bash

set -euo pipefail

SCRIPT_NAME="sysadmin_monitor"
LOG_DIR="/var/log/${SCRIPT_NAME}"
REPORT_FILE="${LOG_DIR}/report_$(date +%Y%m%d_%H%M%S).log"
CONFIG_FILE="/etc/${SCRIPT_NAME}/config.conf"
LOCK_FILE="/var/run/${SCRIPT_NAME}.lock"
ALERT_THRESHOLD_CPU=80
ALERT_THRESHOLD_MEM=85
ALERT_THRESHOLD_DISK=90
RETENTION_DAYS=30

[[ ! -d "$LOG_DIR" ]] && mkdir -p "$LOG_DIR"

exec 200>"$LOCK_FILE"
flock -n 200 || { echo "Script already running"; exit 1; }

trap cleanup EXIT INT TERM

cleanup() {
    rm -f "$LOCK_FILE"
    [[ -n "${TEMP_DIR:-}" ]] && rm -rf "$TEMP_DIR"
}

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$REPORT_FILE"
}

send_alert() {
    local severity=$1
    local message=$2
    logger -t "$SCRIPT_NAME" -p "user.${severity}" "$message"
    
    if command -v mail &> /dev/null; then
        echo "$message" | mail -s "[${severity^^}] System Alert from $(hostname)" root
    fi
    
    if [[ -f /usr/bin/wall ]]; then
        echo "$message" | wall
    fi
}

check_cpu() {
    log "=== CPU Analysis ==="
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
    local load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',')
    
    log "CPU Usage: ${cpu_usage}%"
    log "Load Average (1m): ${load_avg}"
    
    if (( $(echo "$cpu_usage > $ALERT_THRESHOLD_CPU" | bc -l) )); then
        send_alert "warning" "CPU usage is high: ${cpu_usage}%"
    fi
    
    log "Top 5 CPU-consuming processes:"
    ps aux --sort=-%cpu | head -6 | tail -5 >> "$REPORT_FILE"
}

check_memory() {
    log "=== Memory Analysis ==="
    local mem_info=$(free -m | awk 'NR==2{printf "Used: %sMB (%.2f%%), Available: %sMB\n", $3, $3*100/$2, $7}')
    local mem_percent=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    
    log "$mem_info"
    
    if [[ $mem_percent -gt $ALERT_THRESHOLD_MEM ]]; then
        send_alert "warning" "Memory usage is high: ${mem_percent}%"
    fi
    
    log "Top 5 memory-consuming processes:"
    ps aux --sort=-%mem | head -6 | tail -5 >> "$REPORT_FILE"
}

check_disk() {
    log "=== Disk Analysis ==="
    
    while IFS= read -r line; do
        local usage=$(echo "$line" | awk '{print $5}' | tr -d '%')
        local mount=$(echo "$line" | awk '{print $6}')
        
        log "Mount: $mount - Usage: ${usage}%"
        
        if [[ $usage -gt $ALERT_THRESHOLD_DISK ]]; then
            send_alert "critical" "Disk usage critical on ${mount}: ${usage}%"
        fi
    done < <(df -h | grep -vE '^Filesystem|tmpfs|cdrom')
    
    log "Inode usage:"
    df -i | grep -vE '^Filesystem|tmpfs' >> "$REPORT_FILE"
}

check_services() {
    log "=== Critical Services Status ==="
    local services=("sshd" "cron" "rsyslog" "nginx" "mysql" "docker")
    
    for service in "${services[@]}"; do
        if systemctl list-unit-files | grep -q "^${service}.service"; then
            if systemctl is-active --quiet "$service"; then
                log "✓ $service is running"
            else
                log "✗ $service is NOT running"
                send_alert "error" "Service $service is down on $(hostname)"
                
                log "Attempting to restart $service..."
                if systemctl restart "$service" 2>&1 | tee -a "$REPORT_FILE"; then
                    log "✓ Successfully restarted $service"
                else
                    send_alert "critical" "Failed to restart $service on $(hostname)"
                fi
            fi
        fi
    done
}

check_security() {
    log "=== Security Checks ==="
    
    log "Failed SSH login attempts (last 24h):"
    journalctl -u sshd --since "24 hours ago" | grep -i "failed\|failure" | wc -l >> "$REPORT_FILE"
    
    log "Active connections:"
    ss -tunap | grep ESTABLISHED | wc -l >> "$REPORT_FILE"
    
    log "Checking for rootkits with basic scans..."
    if command -v rkhunter &> /dev/null; then
        rkhunter --check --skip-keypress --report-warnings-only >> "$REPORT_FILE" 2>&1 || true
    fi
    
    log "Recent sudo commands:"
    journalctl _COMM=sudo --since "24 hours ago" | tail -10 >> "$REPORT_FILE" || true
}

check_logs() {
    log "=== Log Analysis ==="
    
    log "Recent errors in syslog:"
    journalctl --priority=err --since "1 hour ago" | tail -20 >> "$REPORT_FILE" || true
    
    log "Disk I/O errors:"
    dmesg | grep -i "i/o error" | tail -10 >> "$REPORT_FILE" || true
}

cleanup_old_logs() {
    log "=== Cleanup Old Logs ==="
    find "$LOG_DIR" -name "report_*.log" -mtime "+${RETENTION_DAYS}" -delete
    log "Removed logs older than ${RETENTION_DAYS} days"
}

rotate_logs() {
    log "=== Log Rotation Check ==="
    if [[ -f /var/log/syslog ]] && [[ $(stat -f%z /var/log/syslog 2>/dev/null || stat -c%s /var/log/syslog) -gt 104857600 ]]; then
        log "Syslog exceeds 100MB, triggering rotation"
        logrotate -f /etc/logrotate.conf 2>&1 | tee -a "$REPORT_FILE"
    fi
}

backup_critical_configs() {
    log "=== Configuration Backup ==="
    local backup_dir="/var/backups/sysadmin_configs/$(date +%Y%m%d)"
    mkdir -p "$backup_dir"
    
    local configs=("/etc/fstab" "/etc/ssh/sshd_config" "/etc/nginx" "/etc/mysql")
    
    for config in "${configs[@]}"; do
        if [[ -e "$config" ]]; then
            cp -a "$config" "$backup_dir/" 2>&1 | tee -a "$REPORT_FILE" || true
            log "Backed up: $config"
        fi
    done
    
    find /var/backups/sysadmin_configs -mtime "+7" -exec rm -rf {} + 2>/dev/null || true
}

system_updates_check() {
    log "=== Available Updates ==="
    
    if command -v apt-get &> /dev/null; then
        apt-get update &> /dev/null
        local updates=$(apt list --upgradable 2>/dev/null | grep -c upgradable || true)
        log "Available package updates: $updates"
        
        if [[ $updates -gt 0 ]]; then
            log "Security updates:"
            apt list --upgradable 2>/dev/null | grep -i security >> "$REPORT_FILE" || true
        fi
    elif command -v yum &> /dev/null; then
        local updates=$(yum check-update --quiet | grep -c "^[a-zA-Z]" || true)
        log "Available package updates: $updates"
    fi
}

network_diagnostics() {
    log "=== Network Diagnostics ==="
    
    log "Network interfaces status:"
    ip -br addr >> "$REPORT_FILE"
    
    log "Checking connectivity to critical hosts:"
    local hosts=("8.8.8.8" "1.1.1.1")
    
    for host in "${hosts[@]}"; do
        if ping -c 2 -W 2 "$host" &> /dev/null; then
            log "✓ Connectivity to $host: OK"
        else
            log "✗ Connectivity to $host: FAILED"
            send_alert "warning" "Cannot reach $host from $(hostname)"
        fi
    done
}

generate_summary() {
    log "=== System Summary ==="
    log "Hostname: $(hostname)"
    log "Uptime: $(uptime -p)"
    log "Kernel: $(uname -r)"
    log "Users logged in: $(who | wc -l)"
    log "Total processes: $(ps aux | wc -l)"
}

main() {
    log "=========================================="
    log "Starting System Administration Monitor"
    log "=========================================="
    
    generate_summary
    check_cpu
    check_memory
    check_disk
    check_services
    check_security
    check_logs
    network_diagnostics
    system_updates_check
    cleanup_old_logs
    rotate_logs
    backup_critical_configs
    
    log "=========================================="
    log "System Administration Monitor Complete"
    log "=========================================="
    
    echo "Report saved to: $REPORT_FILE"
}

main "$@"

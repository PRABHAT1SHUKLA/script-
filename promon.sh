#!/bin/bash
# Monitors a process and restarts it if it dies

PROCESS_NAME="nginx"
LOG_FILE="/var/log/process_monitor.log"
CHECK_INTERVAL=5

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

is_running() {
    pgrep -x "$PROCESS_NAME" > /dev/null 2>&1
}

while true; do
    if ! is_running; then
        log "WARNING: $PROCESS_NAME is not running. Restarting..."
        systemctl start "$PROCESS_NAME" 2>/dev/null || service "$PROCESS_NAME" start 2>/dev/null
        sleep 2
        if is_running; then
            log "SUCCESS: $PROCESS_NAME restarted successfully."
        else
            log "ERROR: Failed to restart $PROCESS_NAME!"
        fi
    else
        log "OK: $PROCESS_NAME is running (PID: $(pgrep -x $PROCESS_NAME))"
    fi
    sleep "$CHECK_INTERVAL"
done

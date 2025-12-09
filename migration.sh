#!/bin/bash

set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly LOG_FILE="/var/log/deploy-$(date +%Y%m%d-%H%M%S).log"
readonly LOCK_FILE="/tmp/deploy.lock"
readonly MAX_RETRIES=3
readonly TIMEOUT=300

ENVIRONMENT="${1:-staging}"
SERVICE_NAME="${2:-api}"
VERSION="${3:-latest}"
ROLLBACK=false

log() {
    local level=$1
    shift
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_FILE"
}

error_exit() {
    log "ERROR" "$1"
    cleanup
    exit 1
}

cleanup() {
    [[ -f "$LOCK_FILE" ]] && rm -f "$LOCK_FILE"
    log "INFO" "Cleanup completed"
}

trap cleanup EXIT
trap 'error_exit "Script interrupted"' INT TERM

acquire_lock() {
    if [[ -f "$LOCK_FILE" ]]; then
        local pid
        pid=$(cat "$LOCK_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            error_exit "Another deployment is running (PID: $pid)"
        else
            log "WARN" "Removing stale lock file"
            rm -f "$LOCK_FILE"
        fi
    fi
    echo $$ > "$LOCK_FILE"
}

check_prerequisites() {
    local deps=("docker" "kubectl" "aws" "jq" "curl")
    for cmd in "${deps[@]}"; do
        command -v "$cmd" >/dev/null 2>&1 || error_exit "$cmd not found"
    done
    
    [[ -n "${AWS_PROFILE:-}" ]] || error_exit "AWS_PROFILE not set"
    kubectl config current-context >/dev/null 2>&1 || error_exit "kubectl context not configured"
}

fetch_config() {
    log "INFO" "Fetching configuration for $ENVIRONMENT"
    
    aws ssm get-parameter \
        --name "/config/$ENVIRONMENT/$SERVICE_NAME" \
        --with-decryption \
        --query 'Parameter.Value' \
        --output text > /tmp/config.json || error_exit "Failed to fetch config"
    
    export DB_HOST=$(jq -r '.database.host' /tmp/config.json)
    export DB_PORT=$(jq -r '.database.port' /tmp/config.json)
    export REDIS_URL=$(jq -r '.redis.url' /tmp/config.json)
}

health_check() {
    local endpoint=$1
    local retries=0
    
    while [[ $retries -lt $MAX_RETRIES ]]; do
        if curl -sf --max-time 10 "$endpoint/health" >/dev/null 2>&1; then
            log "INFO" "Health check passed for $endpoint"
            return 0
        fi
        retries=$((retries + 1))
        log "WARN" "Health check failed, retry $retries/$MAX_RETRIES"
        sleep 5
    done
    
    return 1
}

backup_database() {
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="backup_${SERVICE_NAME}_${timestamp}.sql"
    
    log "INFO" "Creating database backup"
    
    PGPASSWORD="${DB_PASSWORD}" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -F c \
        -f "/backups/$backup_file" || error_exit "Database backup failed"
    
    aws s3 cp "/backups/$backup_file" \
        "s3://backups-${ENVIRONMENT}/${SERVICE_NAME}/$backup_file" \
        --storage-class STANDARD_IA || log "WARN" "S3 backup upload failed"
    
    log "INFO" "Backup completed: $backup_file"
}

run_migrations() {
    log "INFO" "Running database migrations"
    
    kubectl run migration-job-$$ \
        --image="registry.internal/${SERVICE_NAME}:${VERSION}" \
        --restart=Never \
        --command -- /app/migrate.sh || error_exit "Migration failed"
    
    kubectl wait --for=condition=complete --timeout=${TIMEOUT}s job/migration-job-$$ || error_exit "Migration timeout"
    kubectl delete job migration-job-$$ --ignore-not-found=true
}

deploy_service() {
    log "INFO" "Deploying $SERVICE_NAME:$VERSION to $ENVIRONMENT"
    
    local current_replicas
    current_replicas=$(kubectl get deployment "$SERVICE_NAME" -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "3")
    
    kubectl set image deployment/"$SERVICE_NAME" \
        "${SERVICE_NAME}=registry.internal/${SERVICE_NAME}:${VERSION}" \
        --record || error_exit "Image update failed"
    
    kubectl rollout status deployment/"$SERVICE_NAME" \
        --timeout=${TIMEOUT}s || {
        log "ERROR" "Deployment failed, initiating rollback"
        kubectl rollout undo deployment/"$SERVICE_NAME"
        error_exit "Deployment failed and rolled back"
    }
    
    kubectl scale deployment/"$SERVICE_NAME" --replicas="$current_replicas"
}

verify_deployment() {
    log "INFO" "Verifying deployment"
    
    local pods
    pods=$(kubectl get pods -l "app=$SERVICE_NAME" -o json)
    local running_count
    running_count=$(echo "$pods" | jq '[.items[] | select(.status.phase=="Running")] | length')
    
    [[ $running_count -gt 0 ]] || error_exit "No running pods found"
    
    local service_url
    service_url=$(kubectl get svc "$SERVICE_NAME" -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
    
    health_check "http://${service_url}" || error_exit "Post-deployment health check failed"
}

update_metrics() {
    local metric_data
    metric_data=$(cat <<EOF
{
    "deployment": {
        "service": "$SERVICE_NAME",
        "version": "$VERSION",
        "environment": "$ENVIRONMENT",
        "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
        "status": "success"
    }
}
EOF
)
    
    curl -X POST "https://metrics.internal/api/deployments" \
        -H "Content-Type: application/json" \
        -d "$metric_data" >/dev/null 2>&1 || log "WARN" "Metrics update failed"
}

send_notification() {
    local status=$1
    local message=$2
    
    aws sns publish \
        --topic-arn "arn:aws:sns:us-east-1:123456789:deployments" \
        --subject "Deployment $status: $SERVICE_NAME" \
        --message "$message" >/dev/null 2>&1 || log "WARN" "SNS notification failed"
}

main() {
    log "INFO" "Starting deployment process"
    log "INFO" "Environment: $ENVIRONMENT, Service: $SERVICE_NAME, Version: $VERSION"
    
    acquire_lock
    check_prerequisites
    fetch_config
    backup_database
    run_migrations
    deploy_service
    verify_deployment
    update_metrics
    
    send_notification "SUCCESS" "Deployed $SERVICE_NAME:$VERSION to $ENVIRONMENT"
    log "INFO" "Deployment completed successfully"
}

main "$@"

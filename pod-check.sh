#!/bin/bash




RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
TIMEOUT=5
LOGFILE="health_check_$(date +%Y%m%d_%H%M%S).log"

declare -a ENDPOINTS=(
    "Frontend|https://frontend.example.com/health|https"
    "Backend API|https://api.example.com/health|https"
    "Database|db.example.com:5432|tcp"
    "Redis Cache|redis.example.com:6379|tcp"
    "Monitoring|monitor.example.com|icmp"
)

# Kubernetes namespace (optional, leave empty if not using K8s)
K8S_NAMESPACE=""

# Function to check HTTP/HTTPS endpoint
check_http() {
    local url=$1
    local response=$(curl -s -o /dev/null -w "%{http_code}" --max-time $TIMEOUT "$url" 2>&1)
    
    if [[ $response -ge 200 && $response -lt 400 ]]; then
        return 0
    else
        return 1
    fi
}

# Function to check TCP port
check_tcp() {
    local host=$(echo $1 | cut -d':' -f1)
    local port=$(echo $1 | cut -d':' -f2)
    
    timeout $TIMEOUT bash -c "cat < /dev/null > /dev/tcp/$host/$port" 2>/dev/null
    return $?
}

# Function to check ICMP (ping)
check_icmp() {
    local host=$1
    ping -c 1 -W $TIMEOUT "$host" > /dev/null 2>&1
    return $?
}

# Function to check Kubernetes pod status (optional)
check_k8s_pod() {
    local pod_name=$1
    local namespace=${2:-$K8S_NAMESPACE}
    
    if ! command -v kubectl &> /dev/null; then
        return 2 # kubectl not found
    fi
    
    local status=$(kubectl get pod -n "$namespace" -l app="$pod_name" -o jsonpath='{.items[0].status.phase}' 2>/dev/null)
    
    if [[ "$status" == "Running" ]]; then
        return 0
    else
        return 1
    fi
}

# Function to log results
log_result() {
    echo -e "$1" | tee -a "$LOGFILE"
}

# Main health check function
check_endpoint() {
    local name=$1
    local target=$2
    local type=$3
    local status=""
    local result=1
    
    case $type in
        http|https)
            if check_http "$target"; then
                status="${GREEN}✓ UP${NC}"
                result=0
            else
                status="${RED}✗ DOWN${NC}"
                result=1
            fi
            ;;
        tcp)
            if check_tcp "$target"; then
                status="${GREEN}✓ UP${NC}"
                result=0
            else
                status="${RED}✗ DOWN${NC}"
                result=1
            fi
            ;;
        icmp)
            if check_icmp "$target"; then
                status="${GREEN}✓ UP${NC}"
                result=0
            else
                status="${RED}✗ DOWN${NC}"
                result=1
            fi
            ;;
        *)
            status="${YELLOW}? UNKNOWN TYPE${NC}"
            result=2
            ;;
    esac
    
    printf "%-30s %-40s %b\n" "$name" "$target" "$status"
    return $result
}

# Main execution
echo "=========================================="
echo "Deployment Health Check"
echo "Started at: $(date)"
echo "=========================================="
echo ""

total=0
up=0
down=0

for endpoint in "${ENDPOINTS[@]}"; do
    IFS='|' read -r name url type <<< "$endpoint"
    ((total++))
    
    if check_endpoint "$name" "$url" "$type"; then
        ((up++))
    else
        ((down++))
    fi
done

echo ""
echo "=========================================="
echo "Summary:"
echo "Total Endpoints: $total"
echo -e "Up:   ${GREEN}$up${NC}"
echo -e "Down: ${RED}$down${NC}"
echo "=========================================="
echo "Log saved to: $LOGFILE"


if [ $down -gt 0 ]; then
    exit 1
else
    exit 0
fi

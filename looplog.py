

THRESHOLD_CPU=80
THRESHOLD_MEM=70
SLEEP_TIME=5 # Check every 5 seconds

while true; do
    # Get CPU and Memory usage using top command parsing
    CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    MEM_USAGE=$(free -m | grep Mem | awk '{print $3/$2 * 100.0}')

    echo "$(date): CPU: ${CPU_USAGE}% | Memory: ${MEM_USAGE}%"

    if (( $(echo "$CPU_USAGE > $THRESHOLD_CPU" | bc -l) )); then
        echo "ALERT: High CPU usage detected: ${CPU_USAGE}%"
    fi

    if (( $(echo "$MEM_USAGE > $THRESHOLD_MEM" | bc -l) )); then
        echo "ALERT: High Memory usage detected: ${MEM_USAGE}%"
    fi

    sleep $SLEEP_TIME
done

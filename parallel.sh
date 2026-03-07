#!/bin/bash
# Run jobs in parallel with a max concurrency limit

MAX_JOBS=4
SEMAPHORE="/tmp/sem_$$"
mkdir -p "$SEMAPHORE"

acquire_slot() {
    while true; do
        count=$(ls "$SEMAPHORE" | wc -l)
        if (( count < MAX_JOBS )); then
            touch "$SEMAPHORE/$$_$RANDOM"
            return
        fi
        sleep 0.1
    done
}

release_slot() {
    rm -f "$SEMAPHORE"/$$_*
}

cleanup() {
    rm -rf "$SEMAPHORE"
    wait
}
trap cleanup EXIT

process_item() {
    local item=$1
    acquire_slot
    (
        echo "Processing: $item (PID $$)"
        sleep $((RANDOM % 3 + 1))   # simulate work
        echo "Done: $item"
        release_slot
    ) &
}

# Feed items
for i in {1..12}; do
    process_item "task_$i"
done

wait
echo "All jobs completed."

#!/bin/bash
# Oricli-Alpha Log Watchdog
# Truncates runaway logs to prevent disk exhaustion

MAX_SIZE_MB=1024
LOGS=("/home/mike/Mavaia/go_backbone.log" "/home/mike/Mavaia/api_daemon.log")

for LOG_FILE in "${LOGS[@]}"; do
    if [ -f "$LOG_FILE" ]; then
        SIZE_KB=$(du -k "$LOG_FILE" | cut -f1)
        SIZE_MB=$((SIZE_KB / 1024))
        
        if [ $SIZE_MB -gt $MAX_SIZE_MB ]; then
            echo "$(date): Truncating $LOG_FILE ($SIZE_MB MB > $MAX_SIZE_MB MB)" >> /home/mike/Mavaia/watchdog.log
            truncate -s 0 "$LOG_FILE"
        fi
    fi
done

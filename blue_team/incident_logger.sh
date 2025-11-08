#!/bin/bash

LOG="incident_log.txt"
echo "[+] Incident Logger Started. Ctrl+C to exit."
while true; do
    read -p ">> Log entry: " ENTRY
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $ENTRY" >> "$LOG"
done


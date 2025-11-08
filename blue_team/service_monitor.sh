#!/usr/bin/env bash
set -euo pipefail

# Services present on your box (adjust as needed)
SERVICES=("apache2" "ssh" "mariadb")
INTERVAL=30

# Track last-known states to avoid repeating the same log
declare -A LAST

log() { logger -t blue-monitor "$*"; echo "$*" >> service_status.log; }

while true; do
  for SVC in "${SERVICES[@]}"; do
    if systemctl is-active --quiet "$SVC"; then
      if [[ "${LAST[$SVC]:-unknown}" != "up" ]]; then
        log "[+] $SVC is UP at $(date)"
        LAST[$SVC]="up"
      fi
    else
      # Try to restart when down
      if [[ "${LAST[$SVC]:-unknown}" != "down" ]]; then
        log "[!] $SVC is DOWN at $(date); attempting restart…"
      fi
      if systemctl restart "$SVC"; then
        sleep 1
        if systemctl is-active --quiet "$SVC"; then
          log "[+] $SVC restarted successfully at $(date)"
          LAST[$SVC]="up"
        else
          log "[-] $SVC restart attempted but still DOWN at $(date)"
          LAST[$SVC]="down"
        fi
      else
        log "[-] Failed to invoke restart for $SVC at $(date)"
        LAST[$SVC]="down"
      fi
    fi
  done
  sleep "$INTERVAL"
done

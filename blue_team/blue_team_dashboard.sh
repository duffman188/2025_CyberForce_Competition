#!/usr/bin/env bash
# blue_team_dashboard.sh — Portable Blue Team Toolkit launcher
# Place in ~/cyber_tools/blue_team/ and make executable.

set -Eeuo pipefail
trap 'echo -e "\n${RED}[!] Exiting due to error (line $LINENO).${NC}"; exit 1' ERR
trap 'echo -e "\n${YELLOW}[i] Returning to menu...${NC}";' SIGINT

# Resolve script directory (portable, works through symlinks)
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# Color helpers
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
NC="\033[0m"

# Banner (multi-line)
BANNER="${GREEN}
   ____  _            _     _______                          _
  | __ )| | ___   ___| | __|__   __|__ _ _ __ ___  ___ _ __ | |__
  |  _ \| |/ _ \ / __| |/ /  | | / _ \ '__/ _ \/ _ \ '_ \| '_ \\
  | |_) | | (_) | (__|   <   | ||  __/ | |  __/  __/ |_) | | | |
  |____/|_|\___/ \___|_|\_\  |_| \___|_|  \___|\___| .__/|_| |_|
                                                   |_|
${NC}"

clear
echo -e "$BANNER"
echo -e "${YELLOW}[+] Blue Team Toolkit Loaded — $(date)${NC}"

# Helpers
require_executable() {
  local path="$1"
  if [[ ! -e "$path" ]]; then
    echo -e "${RED}[!] Missing: $path${NC}"
    return 2
  fi
  if [[ ! -x "$path" ]]; then
    echo -e "${YELLOW}[!] $path exists but is not executable. Attempting to set +x...${NC}"
    chmod +x "$path" || { echo -e "${RED}[!] Failed to chmod +x $path${NC}"; return 3; }
  fi
  return 0
}

run_script() {
  local script="$1"
  require_executable "$script" || return $?
  echo -e "${YELLOW}[*] Running: $(basename "$script") (Ctrl+C to stop)...${NC}"
  bash "$script"
  local rc=$?
  echo -e "${GREEN}[+] $(basename "$script") exited with code $rc${NC}"
  return $rc
}

press_any_key() {
  read -r -s -n1 -p $'\nPress any key to continue...' dummy
  echo
}

# Main menu loop
while true; do
  echo -e "\n${GREEN}Choose a defense utility:${NC}"
  echo -e "1) Secure Linux system"
  echo -e "2) Start service monitor"
  echo -e "3) Manual incident logger"
  echo -e "4) Run hardening audit"
  echo -e "5) Upload logs to remote (scp)"
  echo -e "6) Exit"

  read -r -p $'\n> Option: ' CHOICE || CHOICE="6"

  case "$CHOICE" in
    1)
      run_script "$script_dir/secure_linux.sh" || true
      press_any_key
      ;;
    2)
      run_script "$script_dir/service_monitor.sh" || true
      press_any_key
      ;;
    3)
      run_script "$script_dir/incident_logger.sh" || true
      press_any_key
      ;;
    4)
      run_script "$script_dir/quick_hardening_audit.sh" || true
      press_any_key
      ;;
    5)
      # Upload logs to remote via scp
      echo -e "${YELLOW}[?] Upload logs to remote host via scp${NC}"
      read -r -p "Local file or directory to upload (e.g. service_status.log or /var/log/syslog): " LOCALPATH
      if [[ -z "$LOCALPATH" ]]; then
        echo -e "${RED}[!] No local path provided.${NC}"
        press_any_key
        continue
      fi
      if [[ ! -e "$LOCALPATH" ]]; then
        echo -e "${RED}[!] Local path does not exist: $LOCALPATH${NC}"
        press_any_key
        continue
      fi
      read -r -p "Remote user@host (e.g. user@10.0.0.5): " REMOTE
      read -r -p "Destination path on remote (e.g. /tmp/): " DEST
      if [[ -z "$REMOTE" || -z "$DEST" ]]; then
        echo -e "${RED}[!] Remote or destination not provided.${NC}"
        press_any_key
        continue
      fi
      if ! command -v scp >/dev/null 2>&1; then
        echo -e "${RED}[!] scp not found. Install openssh-client / openssh-server as needed.${NC}"
        press_any_key
        continue
      fi
      echo -e "${YELLOW}[i] Uploading $LOCALPATH -> ${REMOTE}:$DEST${NC}"
      scp -r "$LOCALPATH" "${REMOTE}:$DEST" && echo -e "${GREEN}[+] Upload successful.${NC}" || echo -e "${RED}[!] Upload failed.${NC}"
      press_any_key
      ;;
    6|q|Q|exit)
      echo -e "${GREEN}[+] Goodbye.${NC}"
      exit 0
      ;;
    *)
      echo -e "${RED}[!] Invalid choice. Please enter 1-6.${NC}"
      ;;
  esac
done


#!/usr/bin/env python3
"""
Log shipper that tails common log files or falls back to `journalctl -f`.
Posts matching lines to the SOC dashboard /ingest endpoint.
"""
import os, time, json, requests, shutil, subprocess
from pathlib import Path

# --- Config ---
SOC_URL  = "http://192.168.122.140:5000/ingest"   # change if needed
KEYWORDS = ["Failed password", "authentication failure", "error", "unauthorized", "brute", "invalid user"]
CANDIDATE_FILES = [
    "/var/log/auth.log",   # Debian/Ubuntu
    "/var/log/secure",     # RHEL/CentOS
    "/var/log/syslog",     # some systems
    "/var/log/messages"
]

# --- Helpers ---
def send_alert(msg):
    payload = {"summary": msg, "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
    try:
        requests.post(SOC_URL, data={"summary": json.dumps(payload)}, timeout=3)
        print(f"[+] Sent alert: {msg}")
    except Exception as e:
        print(f"[!] Failed to send alert: {e}")

def tail_file(path):
    """Yield new lines appended to path (like tail -F)."""
    with open(path, "r", errors="ignore") as fh:
        fh.seek(0, 2)
        while True:
            line = fh.readline()
            if not line:
                time.sleep(0.5)
                continue
            yield line.rstrip("\n")

def tail_journal():
    """Yield lines from `journalctl -f -o cat` subprocess."""
    cmd = ["journalctl", "-f", "-o", "cat"]
    # If journalctl isn't readable without sudo, we'll notify the user.
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except FileNotFoundError:
        raise RuntimeError("journalctl not found on this system.")
    if p.stdout is None:
        raise RuntimeError("journalctl stdout not available.")
    print("[*] Tailing systemd journal via: {}".format(" ".join(cmd)))
    for line in p.stdout:
        yield line.rstrip("\n")

def choose_source():
    for p in CANDIDATE_FILES:
        if Path(p).exists():
            print(f"[*] Using log file: {p}")
            return ("file", p)
    # none found -> fallback to journal
    print("[*] No common log files found; will attempt to read systemd journal (journalctl -f).")
    return ("journal", None)

# --- Main ---
def main():
    print("[*] Starting log-shipper")
    mode, src = choose_source()
    if mode == "file":
        try:
            for line in tail_file(src):
                if any(k.lower() in line.lower() for k in KEYWORDS):
                    send_alert(line)
        except PermissionError:
            print(f"[!] Permission denied reading {src}. Run with sudo or add your user to the 'adm' group.")
    else:
        # journal mode - user may need sudo to read system logs
        # Try to run journalctl; if permission denied, suggest sudo
        try:
            for line in tail_journal():
                if any(k.lower() in line.lower() for k in KEYWORDS):
                    send_alert(line)
        except RuntimeError as e:
            print("[!] Error while reading journal:", e)
            print("[!] Try running: sudo journalctl -f -o cat")
        except PermissionError:
            print("[!] Permission denied for journalctl. Try running with sudo or add user to group 'systemd-journal'/'adm'.")

if __name__ == "__main__":
    main()


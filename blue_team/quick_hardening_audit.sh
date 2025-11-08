#!/bin/bash

echo "[*] World-writable files:"
find / -xdev -type f -perm -0002 -ls 2>/dev/null

echo "[*] Users with UID 0 (should only be root):"
awk -F: '$3 == 0 { print $1 }' /etc/passwd

echo "[*] SSH config:"
grep -iE "PermitRootLogin|PasswordAuthentication" /etc/ssh/sshd_config


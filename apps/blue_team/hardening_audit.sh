#!/usr/bin/env bash
# Quick Hardening Audit — v2 (read-only)
# Usage: sudo ./hardening_audit.sh
# Notes: prints only; does not modify system

PATH="/usr/sbin:/sbin:/usr/bin:/bin:$PATH"

hr() { printf "\n%s\n" "================================================================================"; }
hdr() { hr; echo "[*] $*"; }

have() { command -v "$1" >/dev/null 2>&1; }

# Basic host info
hdr "Host / OS / Kernel"
echo "Hostname: $(hostname -f 2>/dev/null || hostname)"
echo "OS: $(grep -h ^PRETTY_NAME= /etc/os-release 2>/dev/null | cut -d= -f2- | tr -d '"')"
echo "Kernel: $(uname -srmo)"
echo "Uptime: $(uptime -p 2>/dev/null || uptime)"

# Accounts & auth
hdr "Users with UID 0 (should only be root)"
awk -F: '$3 == 0 { print "- " $1 }' /etc/passwd

hdr "Login-capable users (have valid shells)"
awk -F: '($7 ~ /(bash|zsh|fish|sh|ksh)$/){print "- " $1 " -> " $7}' /etc/passwd

hdr "Password hashes disabled/locked (LK/!/*)"
awk -F: 'length($2)>0 && $2 !~ /^\*/ && $2 !~ /^!/{next} {print "- " $1 " -> " $2}' /etc/shadow 2>/dev/null || echo "(need root)"

hdr "Recent failed auth attempts (last 50)"
if have journalctl; then journalctl -q -xe -n 50 2>/dev/null | grep -Ei 'fail|invalid|denied|authentication' || echo "(none seen)"
elif [ -f /var/log/auth.log ]; then tail -n 200 /var/log/auth.log | grep -Ei 'fail|invalid|denied|authentication' || echo "(none seen)"
else echo "(no journalctl or auth.log)"; fi

# Sudo
hdr "Sudoers with NOPASSWD (risk if broad)"
if have getent; then
  getent group sudo wheel 2>/dev/null
fi
grep -RIn --include='*sudoers*' NOPASSWD /etc/sudoers /etc/sudoers.d 2>/dev/null || echo "(none)"

# SSH
SSH_MAIN="/etc/ssh/sshd_config"
hdr "SSH Server Config (effective key directives)"
if [ -f "$SSH_MAIN" ]; then
  # Include snippets
  echo "Config files:" "$SSH_MAIN" /etc/ssh/sshd_config.d/*.conf 2>/dev/null
  grep -Ei '^(Include|Port|AddressFamily|ListenAddress|PermitRootLogin|PasswordAuthentication|PubkeyAuthentication|KbdInteractiveAuthentication|ChallengeResponseAuthentication|X11Forwarding|AllowUsers|AllowGroups|DenyUsers|DenyGroups|Ciphers|MACs|KexAlgorithms)\b' \
    "$SSH_MAIN" /etc/ssh/sshd_config.d/*.conf 2>/dev/null | sed 's/^/- /'
else
  echo "sshd_config not found"
fi

hdr "SSH quick findings"
sshd -T 2>/dev/null | awk '
/^permitrootlogin/{print "- PermitRootLogin: "$2}
/^passwordauthentication/{print "- PasswordAuthentication: "$2}
/^pubkeyauthentication/{print "- PubkeyAuthentication: "$2}
/^x11forwarding/{print "- X11Forwarding: "$2}
/^ciphers|^macs|^kexalgorithms/{print "- "$0}
' || echo "(sshd -T unavailable / need root)"

# Filesystem hygiene
hdr "World-writable files (top 50) (exclude /proc,/sys,/dev tmpfs)"
find / -xdev -type f -perm -0002 -printf "%p %m %u:%g\n" 2>/dev/null | head -n 50 || true

hdr "World-writable directories without sticky bit (top 50)"
find / -xdev -type d -perm -0002 ! -perm -1000 -printf "%p %m %u:%g\n" 2>/dev/null | head -n 50 || true

hdr "SUID/SGID binaries (top 100)"
find / -xdev \( -perm -4000 -o -perm -2000 \) -type f -printf "%m %u:%g %p\n" 2>/dev/null | sort | head -n 100

hdr "Files with no owner or no group"
find / -xdev \( -nouser -o -nogroup \) -printf "%p %m %u:%g\n" 2>/dev/null | head -n 50 || true

# Sensitive file perms
hdr "Sensitive file permissions"
for f in /etc/passwd /etc/shadow /etc/group /etc/gshadow /etc/sudoers; do
  [ -e "$f" ] && stat -c "%a %U:%G %n" "$f" 2>/dev/null
done
[ -d /etc/ssh ] && find /etc/ssh -maxdepth 1 -type f -name "ssh_host_*" -exec stat -c "%a %U:%G %n" {} \; 2>/dev/null

# Services / exposure
hdr "Listening sockets (TCP/UDP)"
if have ss; then
  ss -tulpen 2>/dev/null | sed 's/^/- /'
else
  netstat -tulpen 2>/dev/null | sed 's/^/- /'
fi

hdr "Top processes by network usage (if available)"
have ss && ss -tpnH 2>/dev/null | awk '{print $6}' | cut -d, -f2 | cut -d= -f2 | sort | uniq -c | sort -nr | head -n 20

# Firewall / packet filter
hdr "Firewall status (nftables/iptables/ufw/firewalld)"
if have nft; then echo "- nft ruleset:"; nft list ruleset 2>/dev/null | sed 's/^/  /' | head -n 200; fi
if have iptables; then echo "- iptables -S (filter):"; iptables -S 2>/dev/null | sed 's/^/  /' | head -n 120; fi
if have ufw; then echo "- ufw status:"; ufw status 2>/dev/null; fi
if have firewall-cmd; then echo "- firewalld zones:"; firewall-cmd --get-active-zones 2>/dev/null; fi

# Packages / updates
hdr "Package update status"
if have apt; then
  apt -s upgrade 2>/dev/null | awk '/^Inst /{print "- "$2" -> "$4" ("$5")"}' | head -n 50
elif have dnf; then
  dnf -q check-update 2>/dev/null | sed 's/^/- /' | head -n 50
elif have yum; then
  yum -q check-update 2>/dev/null | sed 's/^/- /' | head -n 50
elif have pacman; then
  pacman -Qu 2>/dev/null | sed 's/^/- /' | head -n 50
else
  echo "(no known pkg manager found)"
fi

# Logging / auditing
hdr "Syslog & audit status"
if have systemctl; then
  systemctl is-active --quiet rsyslog && echo "- rsyslog: active" || echo "- rsyslog: inactive or not installed"
  systemctl is-active --quiet systemd-journald && echo "- journald: active"
  systemctl is-active --quiet auditd && echo "- auditd: active" || echo "- auditd: inactive or not installed"
else
  ps aux | egrep -i 'rsyslog|auditd|journald' | sed 's/^/- /'
fi

# Kernel hardening toggles (quick sample)
hdr "Kernel/hardening toggles"
for k in kernel.kptr_restrict kernel.randomize_va_space kernel.yama.ptrace_scope net.ipv4.ip_forward net.ipv4.conf.all.rp_filter net.ipv4.conf.default.rp_filter net.ipv4.conf.all.accept_redirects net.ipv4.conf.all.send_redirects net.ipv4.tcp_syncookies; do
  v=$(sysctl -n "$k" 2>/dev/null || echo "N/A")
  printf -- "- %-40s : %s\n" "$k" "$v"
done

# Time sync
hdr "Time sync status"
if have timedatectl; then timedatectl 2>/dev/null | sed 's/^/- /'; else echo "- timedatectl not available"; fi

# Containers / cloud hints
hdr "Containerization hints"
if [ -f /.dockerenv ] || grep -qi docker /proc/1/cgroup 2>/dev/null; then
  echo "- Running inside a container"
else
  echo "- Not detected as container"
fi

hr
echo "[*] Audit complete."


#!/usr/bin/env bash
set -euo pipefail
echo "== restore_network.sh: restarting NetworkManager and requesting DHCP =="
sudo systemctl restart NetworkManager || true
sleep 2

# pick an interface to dhclient on
iface=$(ip -o -4 addr show up scope global | awk '{print $2;exit}')
if [ -n "$iface" ]; then
  echo "Requesting DHCP on $iface"
  sudo dhclient -v "$iface" || sudo dhclient -v || true
else
  echo "No suitable IPv4 interface found. Run: ip -c a"
fi

# Temporary DNS fallback
if [ -w /etc/resolv.conf ] || sudo test -w /etc/resolv.conf; then
  echo "Setting temporary /etc/resolv.conf (Cloudflare + Google)"
  sudo bash -c 'cat > /etc/resolv.conf <<EO
nameserver 1.1.1.1
nameserver 8.8.8.8
EO'
else
  echo "Cannot write /etc/resolv.conf (managed by system). Try 'resolvectl' or nmcli."
fi

echo "Done. Test with: ping -c 3 1.1.1.1 && ping -c 3 google.com"

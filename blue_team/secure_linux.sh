#!/bin/bash

echo "[*] Securing SSH..."
sudo sed -i 's/^#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/^#PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart sshd

echo "[*] Setting password complexity rules..."
sudo apt install -y libpam-pwquality
sudo sed -i 's/^#.*pam_pwquality.so.*/password requisite pam_pwquality.so retry=3 minlen=12 difok=3/' /etc/pam.d/common-password

echo "[*] Enabling UFW firewall..."
sudo ufw allow OpenSSH
sudo ufw enable


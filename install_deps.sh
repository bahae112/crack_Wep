#!/bin/bash
# Installation des dépendances système pour les scripts WEP

# Outils pour l'AP (hostapd + DHCP)
sudo apt-get update
sudo apt-get install -y hostapd dnsmasq iptables

# Outils pour l'attaque WEP (suite Aircrack-ng)
sudo apt-get install -y aircrack-ng

# Outils réseau (iw, iproute2, wireless-tools)
sudo apt-get install -y iw iproute2 wireless-tools net-tools

# (Optionnel) macchanger pour changer l'adresse MAC
sudo apt-get install -y macchanger

echo "[+] Toutes les dépendances système sont installées."

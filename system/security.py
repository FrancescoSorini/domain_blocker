import getpass
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

"""
Modulo di sicurezza applicativa.

Responsabilità:
- Verificare se una password è autorizzata
- Consentire il cambio password
- NON gestisce UI
- NON gestisce stato applicativo
"""

# =========================
# FILE DI STORAGE
# =========================

SECURITY_DIR = Path(__file__).resolve().parent
PASSWORD_FILE = SECURITY_DIR / "admin_password.json"
AUDIT_FILE = SECURITY_DIR / "password_audit.log"

# =========================
# PASSWORD DI DEFAULT (SOLO PRIMO AVVIO)
# =========================
# password: admin123
DEFAULT_PASSWORD_HASH = hashlib.sha256(
    "admin123".encode("utf-8")
).hexdigest()

# =========================
# UTILS INTERNI
# =========================

def _load_password_hash() -> str:
    """
    Carica l'hash della password dal file.
    Se il file non esiste, lo crea con la password di default.
    """
    if not PASSWORD_FILE.exists():
        _save_password_hash(DEFAULT_PASSWORD_HASH)
        return DEFAULT_PASSWORD_HASH

    try:
        data = json.loads(PASSWORD_FILE.read_text(encoding="utf-8"))
        return data.get("password_hash", "")
    except Exception:
        return ""


def _save_password_hash(password_hash: str) -> None:
    """
    Salva l'hash della password su file.
    """
    data = {
        "password_hash": password_hash
    }
    PASSWORD_FILE.write_text(
        json.dumps(data, indent=4),
        encoding="utf-8"
    )


def _hash_password(password: str) -> str:
    """
    Calcola l'hash SHA-256 della password.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _append_audit(event: str, success: bool, reason: str | None = None) -> None:
    """
    Scrive un record di audit in formato JSON lines.
    Non include mai password in chiaro.
    """
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "user": getpass.getuser(),
        "event": event,
        "success": success,
    }
    if reason:
        record["reason"] = reason

    AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def audit_password_change_attempt(success: bool, reason: str | None = None) -> None:
    """
    Registra un tentativo di cambio password.
    """
    _append_audit("change_password", success, reason)


# =========================
# API PUBBLICA
# =========================

def check_password(password: str) -> bool:
    """
    Verifica se la password fornita è corretta.

    :param password: password in chiaro inserita dall'utente
    :return: True se corretta, False altrimenti
    """
    if not password:
        return False

    stored_hash = _load_password_hash()
    return _hash_password(password) == stored_hash


def change_password(current_password: str, new_password: str) -> bool:
    """
    Cambia la password SOLO se quella attuale è corretta.
    """
    if not check_password(current_password):
        audit_password_change_attempt(False, "invalid_current_password")
        return False

    new_hash = _hash_password(new_password)
    _save_password_hash(new_hash)
    audit_password_change_attempt(True)
    return True

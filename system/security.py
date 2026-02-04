import hashlib

"""
Modulo di sicurezza applicativa.

Responsabilità:
- Verificare se una password è autorizzata
- NON gestisce UI
- NON gestisce stato applicativo
- Può essere riutilizzato ovunque (GUI, controller, ecc.)
"""

# =========================
# PASSWORD DI PROVA
# =========================
# Password in chiaro (SOLO PER TEST):
#   admin123
#
# Hash SHA-256 calcolato con:
# hashlib.sha256("admin123".encode("utf-8")).hexdigest()

ADMIN_PASSWORD_HASH = (
    "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9"
)

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

    hashed = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hashed == ADMIN_PASSWORD_HASH

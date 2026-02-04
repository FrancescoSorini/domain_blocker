import json
from pathlib import Path

STATE_DIR = Path(__file__).parent
STATE_FILE = STATE_DIR / "blocker_state.json"


def load_state() -> bool:
    """
    Ritorna True se il blocker era attivo, False altrimenti
    """
    if not STATE_FILE.exists():
        return False

    try:
        data = json.loads(STATE_FILE.read_text())
        return bool(data.get("enabled", False))
    except Exception:
        return False


def save_state(enabled: bool):
    STATE_DIR.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "enabled": enabled
    }, indent=2))

import json
from datetime import datetime, timezone
from pathlib import Path

STATE_DIR = Path(__file__).parent
SCHEDULE_FILE = STATE_DIR / "schedule_state.json"


def _write(data: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    SCHEDULE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def save_interval_schedule(start_hhmm: str, end_hhmm: str) -> None:
    _write({
        "mode": "interval",
        "start": start_hhmm,
        "end": end_hhmm,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })


def save_duration_schedule(end_at_iso: str) -> None:
    _write({
        "mode": "duration",
        "end_at": end_at_iso,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })


def clear_schedule() -> None:
    if SCHEDULE_FILE.exists():
        SCHEDULE_FILE.unlink()


def load_schedule() -> dict | None:
    if not SCHEDULE_FILE.exists():
        return None
    try:
        return json.loads(SCHEDULE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None

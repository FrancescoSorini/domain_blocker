import sys
import ctypes
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow
from system.privileges import is_admin, relaunch_as_admin
from state.blocker_state import load_state


def main():
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "DNSDomainBlocker.App"
        )
    except Exception:
        pass

    def _resource_path(rel_path: str) -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys._MEIPASS) / rel_path
        return Path(__file__).resolve().parent / rel_path

    # =========================
    # Controllo privilegi admin
    # =========================
    if not is_admin():
        relaunch_as_admin()
        return

    # =========================
    # Avvio GUI
    # =========================
    app = QApplication(sys.argv)
    icon_path = _resource_path("assets/app.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = MainWindow()

    window.show()
    # =========================
    # Ripristino stato blocker + recovery
    # =========================
    persisted_enabled = load_state()
    recovery_started = window.run_startup_recovery(persisted_enabled)
    if persisted_enabled and not recovery_started:
        window.append_log("[AUTO] Ripristino stato ATTIVO")
        window.start_blocker()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

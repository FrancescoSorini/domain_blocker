import sys
from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow
from system.privileges import is_admin, relaunch_as_admin
from state.blocker_state import load_state


def main():
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

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

    # =========================
    # Ripristino stato blocker
    # =========================
    if load_state():
        window.append_log("[AUTO] Ripristino stato ATTIVO")
        window.start_blocker()

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

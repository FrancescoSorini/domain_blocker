from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QTextEdit, QLabel,
    QListWidget, QLineEdit, QMessageBox,
    QHBoxLayout, QInputDialog, QToolButton
)

from config.domain_manager import load_domains, add_domain, remove_domain
from gui.controller import AppController
from system.security import check_password, change_password


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("DNS Domain Blocker")
        self.resize(900, 620)
        self.setMinimumSize(820, 560)

        # =========================
        # UI BASE
        # =========================
        self.title_label = QLabel("DNS Domain Blocker")
        self.status_label = QLabel("Stato: INATTIVO")
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)

        self.theme_btn = QToolButton()
        self.theme_btn.setText("☀")
        self.theme_btn.setToolTip("Cambia a light mode")

        self.change_password_icon_btn = QToolButton()
        self.change_password_icon_btn.setText("🔑")
        self.change_password_icon_btn.setToolTip("Cambia password")
        self._apply_theme("dark")

        self.start_btn = QPushButton("Avvia DNS Blocker")
        self.stop_btn = QPushButton("Ferma DNS Blocker")
        self.stop_btn.setEnabled(False)

        # =========================
        # DOMAINS UI
        # =========================
        self.domain_list = QListWidget()
        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText("es: facebook.com")

        self.add_domain_btn = QPushButton("Aggiungi dominio")
        self.remove_domain_btn = QPushButton("Rimuovi selezionato")

        domain_input_layout = QHBoxLayout()
        domain_input_layout.addWidget(self.domain_input)
        domain_input_layout.addWidget(self.add_domain_btn)

        # =========================
        # LAYOUT PRINCIPALE
        # =========================
        layout = QVBoxLayout()
        header_layout = QHBoxLayout()
        header_layout.addWidget(self.title_label)
        header_layout.addStretch(1)
        header_layout.addWidget(self.change_password_icon_btn)
        header_layout.addWidget(self.theme_btn)

        layout.addLayout(header_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)

        layout.addWidget(QLabel("Domini bloccati:"))
        layout.addWidget(self.domain_list)
        layout.addLayout(domain_input_layout)
        layout.addWidget(self.remove_domain_btn)

        layout.addWidget(QLabel("Log:"))
        layout.addWidget(self.log_view)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # =========================
        # CONTROLLER
        # =========================
        self.controller = AppController(self.append_log)

        # =========================
        # SIGNALS
        # =========================
        self.start_btn.clicked.connect(self.start_blocker)
        self.stop_btn.clicked.connect(self.stop_blocker)

        self.add_domain_btn.clicked.connect(self.handle_add_domain)
        self.remove_domain_btn.clicked.connect(self.handle_remove_domain)
        self.theme_btn.clicked.connect(self.toggle_theme)
        self.change_password_icon_btn.clicked.connect(self.change_admin_password)

        self.load_domains_to_ui()

    # =========================
    # UI THEME
    # =========================
    def _apply_theme(self, theme: str):
        self._theme = theme
        style_name = "style.qss" if theme == "dark" else "style_light.qss"
        style_path = Path(__file__).resolve().parent / style_name
        self.setStyleSheet(style_path.read_text(encoding="utf-8"))

        if theme == "dark":
            self.theme_btn.setText("☀")
            self.theme_btn.setToolTip("Cambia a light mode")
        else:
            self.theme_btn.setText("☾")
            self.theme_btn.setToolTip("Cambia a dark mode")

    def toggle_theme(self):
        next_theme = "light" if self._theme == "dark" else "dark"
        self._apply_theme(next_theme)

    # =========================
    # LOG
    # =========================
    def append_log(self, message: str):
        self.log_view.append(message)

    # =========================
    # PASSWORD MODAL
    # =========================
    def _show_error(self, title: str, message: str):
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle(title)
        box.setText(message)
        box.setMinimumWidth(480)
        box.resize(520, 160)
        box.exec()

    def _get_password_input(self, title: str, prompt: str):
        dialog = QInputDialog(self)
        dialog.setWindowTitle(title)
        dialog.setLabelText(prompt)
        dialog.setTextEchoMode(QLineEdit.EchoMode.Password)
        dialog.setMinimumWidth(480)
        dialog.resize(520, 160)
        ok = dialog.exec()
        return dialog.textValue(), ok

    def request_password(self, action: str) -> bool:
        password, ok = self._get_password_input(
            "Conferma richiesta",
            f"Inserisci la password per {action}:"
        )

        if not ok:
            return False

        if not check_password(password):
            self._show_error(" ", "Password errata")
            return False

        return True

    # =========================
    # DNS BLOCKER
    # =========================
    def start_blocker(self):
        self.controller.start()
        self.status_label.setText("Stato: ATTIVO")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop_blocker(self):
        if not self.request_password("fermare il DNS blocker"):
            self.append_log("[SECURITY] Tentativo di stop bloccato")
            return

        self.controller.stop()
        self.status_label.setText("Stato: INATTIVO")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    # =========================
    # CHANGE PASSWORD
    # =========================
    def change_admin_password(self):
        # 1️⃣ Verifica password attuale
        current_pwd, ok = self._get_password_input(
            "Cambia password",
            "Inserisci la password attuale:"
        )

        if not ok:
            return

        if not check_password(current_pwd):
            self._show_error(" ", "Password attuale errata")
            self.append_log("[SECURITY] Password attuale errata")
            return

        # 2️⃣ Nuova password
        new_pwd, ok = self._get_password_input(
            "Cambia password",
            "Inserisci la nuova password:"
        )

        if not ok or not new_pwd:
            QMessageBox.warning(self, "Errore", "Password non valida")
            return

        # 3️⃣ Conferma nuova password
        confirm_pwd, ok = self._get_password_input(
            "Cambia password",
            "Conferma la nuova password:"
        )

        if not ok or new_pwd != confirm_pwd:
            QMessageBox.warning(self, "Errore", "Le password non coincidono")
            return

        # 4️⃣ Applica cambio
        change_password(current_pwd, new_pwd)

        QMessageBox.information(
            self,
            "Successo",
            "Password aggiornata con successo"
        )
        self.append_log("[SECURITY] Password amministratore aggiornata")


    # =========================
    # DOMAINS UI
    # =========================
    def load_domains_to_ui(self):
        self.domain_list.clear()
        for domain in load_domains():
            self.domain_list.addItem(domain)

    def handle_add_domain(self):
        domain = self.domain_input.text().strip()

        if not domain:
            return

        if " " in domain or "." not in domain:
            QMessageBox.warning(self, "Errore", "Dominio non valido")
            return

        add_domain(domain)
        self.domain_input.clear()
        self.load_domains_to_ui()
        self.append_log(f"Aggiunto dominio bloccato: {domain}")

    def handle_remove_domain(self):
        item = self.domain_list.currentItem()
        if not item:
            return

        domain = item.text()

        if not self.request_password(f"rimuovere il dominio '{domain}'"):
            self.append_log(f"[SECURITY] Tentativo di rimozione bloccato: {domain}")
            return

        remove_domain(domain)
        self.load_domains_to_ui()
        self.append_log(f"Rimosso dominio bloccato: {domain}")

    # =========================
    # CHIUSURA FINESTRA
    # =========================
    def closeEvent(self, event):
        if not self.controller.is_running:
            event.accept()
            return

        if not self.request_password("chiudere l'applicazione"):
            self.append_log("[SECURITY] Chiusura bloccata")
            event.ignore()
            return

        self.append_log("[APP] Arresto DNS blocker prima della chiusura")
        self.controller.stop()
        event.accept()

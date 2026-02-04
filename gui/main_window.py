from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QTextEdit, QLabel,
    QListWidget, QLineEdit, QMessageBox,
    QHBoxLayout, QInputDialog
)

from config.domain_manager import load_domains, add_domain, remove_domain
from gui.controller import AppController
from system.security import check_password


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("DNS Domain Blocker")
        self.resize(700, 500)

        # =========================
        # UI BASE
        # =========================
        self.status_label = QLabel("Stato: INATTIVO")
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)

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

        self.load_domains_to_ui()

    # =========================
    # LOG
    # =========================
    def append_log(self, message: str):
        self.log_view.append(message)

    # =========================
    # PASSWORD MODAL
    # =========================
    def request_password(self, action: str) -> bool:
        password, ok = QInputDialog.getText(
            self,
            "Conferma richiesta",
            f"Inserisci la password per {action}:",
            QLineEdit.EchoMode.Password
        )

        if not ok:
            return False

        if not check_password(password):
            QMessageBox.critical(self, "Accesso negato", "Password errata")
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
        # PROTEZIONE CON PASSWORD
        if not self.request_password("fermare il DNS blocker"):
            self.append_log("[SECURITY] Tentativo di stop bloccato")
            return

        self.controller.stop()
        self.status_label.setText("Stato: INATTIVO")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

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
        remove_domain(domain)
        self.load_domains_to_ui()
        self.append_log(f"Rimosso dominio bloccato: {domain}")

    # =========================
    # CHIUSURA FINESTRA
    # =========================
    def closeEvent(self, event):
        # Se il DNS blocker NON e attivo -> chiudi senza password
        if not self.controller.is_running:
            event.accept()
            return

        # DNS blocker attivo -> serve password
        if not self.request_password("chiudere l'applicazione"):
            self.append_log("[SECURITY] Chiusura bloccata")
            event.ignore()
            return

        # Password OK -> fermiamo il blocker in modo pulito
        self.append_log("[APP] Arresto DNS blocker prima della chiusura")
        self.controller.stop()

        event.accept()

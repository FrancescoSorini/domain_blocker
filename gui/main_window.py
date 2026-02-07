from datetime import datetime, timedelta, time as dt_time
from pathlib import Path

from PyQt6.QtCore import QTime, QTimer
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QTextEdit, QLabel,
    QListWidget, QLineEdit, QMessageBox,
    QHBoxLayout, QInputDialog, QToolButton,
    QDialog, QGroupBox, QTimeEdit, QSpinBox
)

from config.domain_manager import load_domains, add_domain, remove_domain
from gui.controller import AppController
from system.security import (
    check_password,
    change_password,
    audit_password_change_attempt,
)
from system.network import get_current_dns_ipv4, get_current_dns_ipv6, set_dns_automatic
from state.blocker_state import save_state
from state.schedule_state import (
    save_interval_schedule,
    save_duration_schedule,
    load_schedule,
    clear_schedule,
)


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
        self.status_label = QLabel("Stato: INATTIVO 🔴")
        self.schedule_status_label = QLabel("Programmazione: INATTIVA")
        self.schedule_countdown_label = QLabel("Countdown: --")
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)

        self.change_password_icon_btn = QToolButton()
        self.change_password_icon_btn.setText("🔑")
        self.change_password_icon_btn.setToolTip("Cambia password")

        self.schedule_btn = QToolButton()
        self.schedule_btn.setText("⏰")
        self.schedule_btn.setToolTip("Programma blocco")

        self.info_btn = QToolButton()
        self.info_btn.setText("ℹ️")
        self.info_btn.setToolTip("Informazioni")
        self._apply_light_theme()

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
        header_layout.addWidget(self.schedule_btn)
        header_layout.addWidget(self.change_password_icon_btn)
        header_layout.addWidget(self.info_btn)

        layout.addLayout(header_layout)
        status_layout = QHBoxLayout()
        status_layout.addWidget(self.status_label)
        status_layout.addStretch(1)
        status_layout.addWidget(self.schedule_status_label)
        layout.addLayout(status_layout)
        layout.addWidget(self.schedule_countdown_label)
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
        self.change_password_icon_btn.clicked.connect(self.change_admin_password)
        self.schedule_btn.clicked.connect(self.open_schedule_dialog)
        self.info_btn.clicked.connect(self.open_info_dialog)

        self.load_domains_to_ui()

        # =========================
        # SCHEDULER TIMERS
        # =========================
        self._schedule_start_timer = QTimer(self)
        self._schedule_start_timer.setSingleShot(True)
        self._schedule_start_timer.timeout.connect(self._on_schedule_start)

        self._schedule_stop_timer = QTimer(self)
        self._schedule_stop_timer.setSingleShot(True)
        self._schedule_stop_timer.timeout.connect(self._on_schedule_stop)

        self._duration_timer = QTimer(self)
        self._duration_timer.setSingleShot(True)
        self._duration_timer.timeout.connect(self._on_duration_stop)

        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._update_countdown)

        self._schedule_mode = None
        self._schedule_interval_start = None
        self._schedule_interval_end = None
        self._duration_end_dt = None
        self._interval_end_dt = None

        self._apply_saved_schedule()

    # =========================
    # UI THEME
    # =========================
    def _apply_light_theme(self):
        style_path = Path(__file__).resolve().parent / "style_light.qss"
        self.setStyleSheet(style_path.read_text(encoding="utf-8"))

    # =========================
    # STARTUP RECOVERY
    # =========================
    def run_startup_recovery(self, persisted_enabled: bool) -> bool:
        """
        Recovery livello 1:
        - Se lo stato salvato è INATTIVO ma il DNS è su 127.0.0.1,
          chiedi password per ripristinare DHCP.
        - Se password negata, riavvia il blocker per evitare DNS rotto.
        Ritorna True se ha avviato il blocker.
        """
        try:
            current_dns_v4 = get_current_dns_ipv4()
            current_dns_v6 = get_current_dns_ipv6()
        except Exception as exc:
            self.append_log(f"[RECOVERY] Impossibile leggere DNS: {exc}")
            return False

        dns_is_local = any(dns == "127.0.0.1" for dns in current_dns_v4) or any(
            dns == "::1" for dns in current_dns_v6
        )
        if not persisted_enabled and dns_is_local:
            self.append_log("[RECOVERY] DNS locale rilevato con stato INATTIVO")
            self._show_info(
                "Recupero",
                "Rilevato DNS locale attivo con stato INATTIVO.\n"
                "Inserisci la password per ripristinare il DNS."
            )
            if self.request_password("ripristinare il DNS automatico"):
                try:
                    set_dns_automatic()
                    save_state(False)
                    self.append_log("[RECOVERY] DNS ripristinato su automatico")
                    self._show_info(
                        "Recupero completato",
                        "DNS ripristinato su automatico."
                    )
                except Exception as exc:
                    self.append_log(f"[RECOVERY] Ripristino fallito: {exc}")
                return False

            self.append_log("[RECOVERY] Password negata, riavvio blocker")
            self._show_info(
                "Recupero",
                "Password non valida. Il DNS blocker verrà riattivato."
            )
            self.start_blocker()
            return True

        return False

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

    def _show_info(self, title: str, message: str):
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Information)
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
    # SCHEDULER UI
    # =========================
    def open_schedule_dialog(self):
        if self._is_schedule_session_active():
            if not self.request_password("modificare la programmazione attiva"):
                self.append_log("[SECURITY] Modifica programmazione bloccata")
                return

        dialog = QDialog(self)
        dialog.setWindowTitle("Programma blocco")
        dialog.setMinimumWidth(520)
        dialog_layout = QVBoxLayout(dialog)

        # Intervallo orario
        interval_group = QGroupBox("Intervallo orario")
        interval_layout = QHBoxLayout()
        start_time_edit = QTimeEdit()
        start_time_edit.setDisplayFormat("HH:mm")
        start_time_edit.setTime(QTime.currentTime())
        end_time_edit = QTimeEdit()
        end_time_edit.setDisplayFormat("HH:mm")
        end_time_edit.setTime(QTime.currentTime().addSecs(3600))
        interval_apply_btn = QPushButton("Attiva intervallo")

        interval_layout.addWidget(QLabel("Inizio"))
        interval_layout.addWidget(start_time_edit)
        interval_layout.addWidget(QLabel("Fine"))
        interval_layout.addWidget(end_time_edit)
        interval_layout.addWidget(interval_apply_btn)
        interval_group.setLayout(interval_layout)

        # Durata
        duration_group = QGroupBox("Durata")
        duration_layout = QVBoxLayout()

        presets_layout = QHBoxLayout()
        presets = [("15 min", 15), ("30 min", 30), ("1 ora", 60), ("2 ore", 120), ("5 ore", 300)]
        preset_buttons = []
        for label, minutes in presets:
            btn = QPushButton(label)
            preset_buttons.append((btn, minutes))
            presets_layout.addWidget(btn)

        custom_layout = QHBoxLayout()
        hours_spin = QSpinBox()
        hours_spin.setRange(0, 23)
        hours_spin.setPrefix("Ore: ")
        minutes_spin = QSpinBox()
        minutes_spin.setRange(0, 59)
        minutes_spin.setPrefix("Min: ")
        start_duration_btn = QPushButton("Avvia")

        custom_layout.addWidget(hours_spin)
        custom_layout.addWidget(minutes_spin)
        custom_layout.addWidget(start_duration_btn)

        duration_layout.addLayout(presets_layout)
        duration_layout.addLayout(custom_layout)
        duration_group.setLayout(duration_layout)

        #cancel_btn = QPushButton("Annulla programmazione")
        close_btn = QPushButton("Chiudi")

        dialog_layout.addWidget(interval_group)
        dialog_layout.addWidget(duration_group)
        #dialog_layout.addWidget(cancel_btn)
        dialog_layout.addWidget(close_btn)

        def apply_interval():
            start_time = start_time_edit.time().toPyTime()
            end_time = end_time_edit.time().toPyTime()
            self._apply_interval_schedule(start_time, end_time)
            dialog.accept()

        selected_minutes = {"value": None}

        def set_selected_button(selected_btn: QPushButton | None):
            for btn, _ in preset_buttons:
                btn.setStyleSheet("")
            if selected_btn:
                btn_style = "background: #2563eb; color: #ffffff;"
                selected_btn.setStyleSheet(btn_style)

        def select_preset(minutes: int, btn: QPushButton):
            selected_minutes["value"] = minutes
            set_selected_button(btn)

        def apply_selected_duration():
            minutes = selected_minutes["value"]
            if minutes is None:
                minutes = hours_spin.value() * 60 + minutes_spin.value()
            if minutes <= 0:
                self._show_error("Errore", "Durata non valida")
                return
            self._apply_duration_schedule(minutes)
            dialog.accept()

        def cancel_schedule():
            if self._is_schedule_session_active():
                if not self.request_password("annullare la programmazione attiva"):
                    self.append_log("[SECURITY] Annullamento programmazione bloccato")
                    return
            self._clear_schedule_timers()
            self._schedule_mode = None
            self._schedule_interval_start = None
            self._schedule_interval_end = None
            clear_schedule()
            self.append_log("[SCHEDULE] Programmazione annullata")
            self._show_info("Programmazione", "Programmazione annullata.")
            self._set_schedule_active(False)
            dialog.accept()

        interval_apply_btn.clicked.connect(apply_interval)
        for btn, minutes in preset_buttons:
            btn.clicked.connect(lambda _, m=minutes, b=btn: select_preset(m, b))
        start_duration_btn.clicked.connect(apply_selected_duration)
        #cancel_btn.clicked.connect(cancel_schedule)
        close_btn.clicked.connect(dialog.reject)

        dialog.exec()

    def open_info_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("ℹ️ Informazioni sull’applicazione")
        dialog.setMinimumWidth(520)
        layout = QVBoxLayout(dialog)

        info_text = (
            "DNS Domain Blocker è un’applicazione di controllo della navigazione che consente di bloccare l’accesso a specifici domini Internet a livello di sistema, utilizzando un server DNS locale.\n\n"

            "Una volta attivato, il blocco:\n"

            "🔹​ si applica a tutte le applicazioni del computer (browser, app, servizi)\n"

            "🔹​ rimane attivo finché non viene esplicitamente disattivato\n"

            "🔹​ non può essere rimosso accidentalmente\n\n"

            "Chiunque può attivare il blocco DNS, ma solo gli utenti autorizzati possono:\n"

            "🔹​ disattivarlo\n"

            "🔹​ chiudere l’applicazione mentre il blocco è attivo\n"

            "🔹​ rimuovere domini dalla lista\n"

            "🔹​ modificare la password di amministrazione\n\n"

            "Tutte le operazioni sensibili sono protette da password per garantire sicurezza, controllo e responsabilità.\n\n"

            "⚠️ Nota: se il blocco DNS è attivo e l’applicazione viene chiusa in modo non corretto, la navigazione potrebbe risultare temporaneamente limitata fino al ripristino automatico delle impostazioni di rete."
        )
        label = QLabel(info_text)
        label.setWordWrap(True)

        close_btn = QPushButton("Chiudi")
        close_btn.clicked.connect(dialog.accept)

        layout.addWidget(label)
        layout.addWidget(close_btn)
        dialog.exec()

    # =========================
    # SCHEDULER LOGIC
    # =========================
    def _clear_schedule_timers(self):
        self._schedule_start_timer.stop()
        self._schedule_stop_timer.stop()
        self._duration_timer.stop()
        self._countdown_timer.stop()
        self._duration_end_dt = None
        self._interval_end_dt = None
        self._set_countdown_text("--")

    def _is_schedule_session_active(self) -> bool:
        return self._schedule_mode is not None and self.controller.is_running

    def _set_schedule_active(self, active: bool, detail: str | None = None):
        if active:
            label = "Programmazione: ATTIVA"
            if detail:
                label = f"Programmazione: {detail}"
        else:
            label = "Programmazione: INATTIVA"
        self.schedule_status_label.setText(label)

    def _set_countdown_text(self, text: str):
        self.schedule_countdown_label.setText(f"Countdown: {text}")

    def _update_countdown(self):
        end_dt = self._duration_end_dt or self._interval_end_dt
        if not end_dt:
            self._set_countdown_text("--")
            return
        remaining = end_dt - datetime.now()
        total_seconds = int(remaining.total_seconds())
        if total_seconds <= 0:
            self._set_countdown_text("Scaduto")
            return
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        if hours > 0:
            self._set_countdown_text(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        else:
            self._set_countdown_text(f"{minutes:02d}:{seconds:02d}")

    def _apply_saved_schedule(self):
        data = load_schedule()
        if not data:
            return

        mode = data.get("mode")
        if mode == "interval":
            start_str = data.get("start")
            end_str = data.get("end")
            if not start_str or not end_str:
                return
            try:
                start_time = datetime.strptime(start_str, "%H:%M").time()
                end_time = datetime.strptime(end_str, "%H:%M").time()
            except ValueError:
                return
            self._apply_interval_schedule(start_time, end_time, notify=False)
            self.append_log("[SCHEDULE] Intervallo ripristinato da stato")
            return

        if mode == "duration":
            end_at = data.get("end_at")
            if not end_at:
                return
            try:
                end_dt = datetime.fromisoformat(end_at)
            except ValueError:
                return
            now = datetime.now(end_dt.tzinfo) if end_dt.tzinfo else datetime.now()
            if end_dt <= now:
                clear_schedule()
                return
            remaining_minutes = int((end_dt - now).total_seconds() / 60)
            remaining_minutes = max(1, remaining_minutes)
            self._apply_duration_schedule(remaining_minutes, notify=False)
            self.append_log("[SCHEDULE] Durata ripristinata da stato")

    def _schedule_timer(self, timer: QTimer, target_dt: datetime):
        delta_ms = max(0, int((target_dt - datetime.now()).total_seconds() * 1000))
        timer.start(delta_ms)

    def _apply_interval_schedule(self, start_time: dt_time, end_time: dt_time, notify: bool = True):
        self._clear_schedule_timers()
        self._schedule_mode = "interval"
        self._schedule_interval_start = start_time
        self._schedule_interval_end = end_time
        self._set_schedule_active(True, f"ATTIVA {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}")

        now = datetime.now()
        start_dt = datetime.combine(now.date(), start_time)
        end_dt = datetime.combine(now.date(), end_time)

        if end_dt <= start_dt:
            end_dt += timedelta(days=1)

        if now < start_dt:
            self._schedule_timer(self._schedule_start_timer, start_dt)
            self._schedule_timer(self._schedule_stop_timer, end_dt)
        else:
            if now < end_dt:
                self._start_blocker_scheduled()
                self._schedule_timer(self._schedule_stop_timer, end_dt)
            else:
                start_dt += timedelta(days=1)
                end_dt += timedelta(days=1)
                self._schedule_timer(self._schedule_start_timer, start_dt)
                self._schedule_timer(self._schedule_stop_timer, end_dt)

        self._interval_end_dt = end_dt
        self._countdown_timer.start()
        self.append_log(
            f"[SCHEDULE] Intervallo programmato {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
        )
        save_interval_schedule(start_time.strftime("%H:%M"), end_time.strftime("%H:%M"))
        if notify:
            self._show_info(
                "Programmazione",
                f"Intervallo impostato: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}."
            )

    def _apply_duration_schedule(self, minutes: int, notify: bool = True):
        self._clear_schedule_timers()
        self._schedule_mode = "duration"
        self._schedule_interval_start = None
        self._schedule_interval_end = None

        self._start_blocker_scheduled()
        end_dt = datetime.now() + timedelta(minutes=minutes)
        self._duration_end_dt = end_dt
        self._countdown_timer.start()
        self._schedule_timer(self._duration_timer, end_dt)
        self.append_log(f"[SCHEDULE] Durata programmata: {minutes} minuti")
        save_duration_schedule(end_dt.isoformat(timespec="seconds"))
        self._set_schedule_active(True, "ATTIVA (durata personalizzata)")
        if notify:
            self._show_info("Programmazione", f"Blocco attivo per {minutes} minuti.")

    def _on_schedule_start(self):
        if self._schedule_mode != "interval":
            return
        self._start_blocker_scheduled()

    def _on_schedule_stop(self):
        if self._schedule_mode != "interval":
            return
        self._stop_blocker_scheduled(require_password=False)
        if self._schedule_interval_start and self._schedule_interval_end:
            self._apply_interval_schedule(
                self._schedule_interval_start,
                self._schedule_interval_end,
                notify=False
            )

    def _on_duration_stop(self):
        if self._schedule_mode != "duration":
            return
        self._stop_blocker_scheduled(require_password=False)
        self._schedule_mode = None
        clear_schedule()
        self._set_schedule_active(False)
        self._clear_schedule_timers()

    def _start_blocker_scheduled(self):
        self.controller.start()
        self.status_label.setText("Stato: ATTIVO ​🟢​")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.append_log("[SCHEDULE] DNS blocker attivato")

    def _stop_blocker_scheduled(self, require_password: bool = True):
        if require_password and not self.request_password("fermare la sessione di blocco"):
            return False
        self.controller.stop()
        self.status_label.setText("Stato: INATTIVO 🔴")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.append_log("[SCHEDULE] DNS blocker disattivato")
        return True

    # =========================
    # DNS BLOCKER
    # =========================
    def start_blocker(self):
        self.controller.start()
        self.status_label.setText("Stato: ATTIVO ​🟢")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop_blocker(self):
        if not self.request_password("fermare la sessione di blocco"):
            self.append_log("[SECURITY] Tentativo di stop bloccato")
            return

        self.controller.stop()
        self.status_label.setText("Stato: INATTIVO 🔴")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        if self._schedule_mode:
            self._clear_schedule_timers()
            self._schedule_mode = None
            self._schedule_interval_start = None
            self._schedule_interval_end = None
            clear_schedule()
            self._set_schedule_active(False)
            self.append_log("[SCHEDULE] Programmazione disattivata (stop manuale)")

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
            audit_password_change_attempt(False, "invalid_current_password")
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

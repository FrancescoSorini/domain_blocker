from dns.server import start_dns_server

from system.network import (
    refresh_dns_state,
    set_dns_localhost,
    set_dns_automatic
)

from state.blocker_state import save_state


class AppController:
    def __init__(self, log_callback):
        self.log = log_callback
        self.server = None
        self.is_running = False

        # =========================
        # AVVIO APP
        # =========================
        # Leggiamo il DNS attuale e lo salviamo
        # SENZA toccare il sistema
        refresh_dns_state()
        self.log("[INIT] DNS corrente rilevato e salvato")

    # =========================
    # START DNS BLOCKER
    # =========================

    def start(self):
        if self.is_running:
            self.log("[APP] DNS blocker già attivo")
            return

        self.log("[APP] Avvio DNS blocker...")

        try:
            # 1. Imposta DNS locale
            set_dns_localhost()
            self.log("[DNS] DNS impostato su 127.0.0.1")

            # 2. Avvia server DNS
            self.server = start_dns_server()
            self.is_running = True

            save_state(True)
            self.log("[APP] DNS blocker ATTIVO")

        except Exception as e:
            self.log(f"[ERRORE] Avvio fallito: {e}")
            self.is_running = False
            self.server = None

    # =========================
    # STOP DNS BLOCKER
    # =========================

    def stop(self):
        if not self.is_running:
            self.log("[APP] DNS blocker già fermo")
            return

        self.log("[APP] Arresto DNS blocker...")

        try:
            # 1. Ferma server DNS
            if self.server:
                self.server.stop()
                self.server = None
                self.log("[DNS] Server DNS fermato")

            self.is_running = False

            # 2. Ripristina DNS automatico
            set_dns_automatic()
            self.log("[DNS] DNS ripristinato su automatico (DHCP)")

            save_state(False)
            self.log("[APP] DNS blocker DISATTIVO")

        except Exception as e:
            self.log(f"[ERRORE] Arresto fallito: {e}")

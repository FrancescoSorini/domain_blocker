from pathlib import Path
import json
import tempfile
import unittest
from unittest import mock

import config.domain_manager as domain_manager
import state.blocker_state as blocker_state
import system.network as network
import system.security as security
from gui.main_window import MainWindow
from PyQt6.QtWidgets import QApplication


def _get_qt_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class _DummyEvent:
    def __init__(self):
        self.accepted = False
        self.ignored = False

    def accept(self):
        self.accepted = True

    def ignore(self):
        self.ignored = True


class TestSecurity(unittest.TestCase):
    def test_check_password_accepts_correct(self):
        self.assertTrue(security.check_password("admin123"))

    def test_check_password_rejects_wrong(self):
        self.assertFalse(security.check_password("wrong"))

    def test_check_password_rejects_empty(self):
        self.assertFalse(security.check_password(""))


class TestDomainManager(unittest.TestCase):
    def test_save_and_load_domains_sorted_unique_lowercased(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_file = Path(tmp) / "domains.json"
            with mock.patch.object(domain_manager, "DOMAINS_FILE", tmp_file):
                domain_manager.save_domains(["Example.com", "test.com", "example.com"])
                loaded = domain_manager.load_domains()

        self.assertEqual(loaded, ["example.com", "test.com"])

    def test_add_domain_avoids_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_file = Path(tmp) / "domains.json"
            with mock.patch.object(domain_manager, "DOMAINS_FILE", tmp_file):
                domain_manager.save_domains(["example.com"])
                domain_manager.add_domain("Example.com")
                domain_manager.add_domain("test.com")
                loaded = domain_manager.load_domains()

        self.assertEqual(loaded, ["example.com", "test.com"])

    def test_remove_domain(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_file = Path(tmp) / "domains.json"
            with mock.patch.object(domain_manager, "DOMAINS_FILE", tmp_file):
                domain_manager.save_domains(["example.com", "test.com"])
                domain_manager.remove_domain("example.com")
                loaded = domain_manager.load_domains()

        self.assertEqual(loaded, ["test.com"])


class TestBlockerState(unittest.TestCase):
    def test_save_and_load_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            state_file = state_dir / "blocker_state.json"
            with (
                mock.patch.object(blocker_state, "STATE_DIR", state_dir),
                mock.patch.object(blocker_state, "STATE_FILE", state_file),
            ):
                blocker_state.save_state(True)
                self.assertTrue(blocker_state.load_state())

                blocker_state.save_state(False)
                self.assertFalse(blocker_state.load_state())

    def test_load_state_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            state_file = state_dir / "blocker_state.json"
            with (
                mock.patch.object(blocker_state, "STATE_DIR", state_dir),
                mock.patch.object(blocker_state, "STATE_FILE", state_file),
            ):
                self.assertFalse(blocker_state.load_state())

    def test_load_state_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            state_file = state_dir / "blocker_state.json"
            state_file.write_text("not-json")
            with (
                mock.patch.object(blocker_state, "STATE_DIR", state_dir),
                mock.patch.object(blocker_state, "STATE_FILE", state_file),
            ):
                self.assertFalse(blocker_state.load_state())


class TestNetwork(unittest.TestCase):
    def test_get_active_interface(self):
        with mock.patch.object(network, "_run", return_value="Wi-Fi"):
            self.assertEqual(network.get_active_interface(), "Wi-Fi")

    def test_get_current_dns(self):
        with (
            mock.patch.object(network, "get_active_interface", return_value="Wi-Fi"),
            mock.patch.object(network, "_run", return_value="1.1.1.1\n8.8.8.8\n"),
        ):
            self.assertEqual(network.get_current_dns(), ["1.1.1.1", "8.8.8.8"])

    def test_refresh_and_load_dns_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "dns_state.json"
            with (
                mock.patch.object(network, "STATE_PATH", state_path),
                mock.patch.object(network, "get_active_interface", return_value="Wi-Fi"),
                mock.patch.object(network, "get_current_dns", return_value=["1.1.1.1"]),
            ):
                network.refresh_dns_state()
                data = json.loads(state_path.read_text())
                self.assertEqual(data["interface"], "Wi-Fi")
                self.assertEqual(data["dns"], ["1.1.1.1"])

                loaded = network.load_dns_state()
                self.assertEqual(loaded, data)

    def test_load_dns_state_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "dns_state.json"
            with mock.patch.object(network, "STATE_PATH", state_path):
                self.assertIsNone(network.load_dns_state())


class TestMainWindowGui(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = _get_qt_app()

    def test_close_event_when_not_running_allows_close(self):
        with mock.patch("gui.main_window.AppController") as controller_cls:
            controller = controller_cls.return_value
            controller.is_running = False
            window = MainWindow()

        event = _DummyEvent()
        window.closeEvent(event)

        self.assertTrue(event.accepted)
        self.assertFalse(event.ignored)

    def test_close_event_when_running_requires_password(self):
        with mock.patch("gui.main_window.AppController") as controller_cls:
            controller = controller_cls.return_value
            controller.is_running = True
            window = MainWindow()

        event = _DummyEvent()
        with mock.patch.object(window, "request_password", return_value=False):
            window.closeEvent(event)

        self.assertFalse(event.accepted)
        self.assertTrue(event.ignored)
        controller.stop.assert_not_called()

    def test_close_event_when_running_and_password_ok_stops(self):
        with mock.patch("gui.main_window.AppController") as controller_cls:
            controller = controller_cls.return_value
            controller.is_running = True
            window = MainWindow()

        event = _DummyEvent()
        with mock.patch.object(window, "request_password", return_value=True):
            window.closeEvent(event)

        self.assertTrue(event.accepted)
        self.assertFalse(event.ignored)
        controller.stop.assert_called_once()


if __name__ == "__main__":
    unittest.main()

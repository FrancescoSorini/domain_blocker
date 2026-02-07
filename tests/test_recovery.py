import unittest
from unittest import mock

from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow


def _get_qt_app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestStartupRecovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._app = _get_qt_app()

    def _make_window(self) -> MainWindow:
        with mock.patch("gui.main_window.AppController"):
            return MainWindow()

    def test_inactive_dns_local_password_ok_restores(self):
        window = self._make_window()
        window.start_blocker = mock.Mock()

        with (
            mock.patch("gui.main_window.get_current_dns_ipv4", return_value=["127.0.0.1"]),
            mock.patch("gui.main_window.get_current_dns_ipv6", return_value=[]),
            mock.patch.object(window, "request_password", return_value=True),
            mock.patch.object(window, "_show_info"),
            mock.patch("gui.main_window.set_dns_automatic") as set_auto,
            mock.patch("gui.main_window.save_state") as save_state,
        ):
            result = window.run_startup_recovery(False)

        self.assertFalse(result)
        set_auto.assert_called_once()
        save_state.assert_called_once_with(False)
        window.start_blocker.assert_not_called()

    def test_inactive_dns_local_password_ko_restarts(self):
        window = self._make_window()
        window.start_blocker = mock.Mock()

        with (
            mock.patch("gui.main_window.get_current_dns_ipv4", return_value=["127.0.0.1"]),
            mock.patch("gui.main_window.get_current_dns_ipv6", return_value=[]),
            mock.patch.object(window, "request_password", return_value=False),
            mock.patch.object(window, "_show_info"),
            mock.patch("gui.main_window.set_dns_automatic") as set_auto,
        ):
            result = window.run_startup_recovery(False)

        self.assertTrue(result)
        set_auto.assert_not_called()
        window.start_blocker.assert_called_once()

    def test_no_recovery_when_dns_not_local(self):
        window = self._make_window()

        with (
            mock.patch("gui.main_window.get_current_dns_ipv4", return_value=["1.1.1.1"]),
            mock.patch("gui.main_window.get_current_dns_ipv6", return_value=[]),
            mock.patch.object(window, "request_password") as request_password,
            mock.patch.object(window, "_show_info"),
        ):
            result = window.run_startup_recovery(False)

        self.assertFalse(result)
        request_password.assert_not_called()


if __name__ == "__main__":
    unittest.main()

import logging
import sys

from PySide6.QtWidgets import QApplication

import ui.theme as theme
from core.app_logger import setup_logging
from core.constants import APP_VERSION
from utils.paths import resource_path

_log = logging.getLogger(__name__)


def main() -> None:
    """Entry point: validate license, load branding, launch the app."""
    setup_logging()
    _log.info("CleanSheet v%s starting up", APP_VERSION)

    theme.load(resource_path("branding.json"))

    app = QApplication(sys.argv)

    app.setStyleSheet(theme.DARK_QSS)

    # ── License check ──────────────────────────────────────────────────
    from core.license_validator import validate_license, get_days_until_expiry
    result = validate_license()

    if not result.valid:
        from ui.activation_screen import ActivationScreen
        dialog = ActivationScreen(result)
        if dialog.exec() != ActivationScreen.DialogCode.Accepted:
            sys.exit(0)
        # Re-validate to get the now-valid result (for expiry warning etc.)
        result = validate_license()

    # ── Launch main window ─────────────────────────────────────────────
    from ui.app import App
    window = App()
    window.show()
    _log.info("Main window displayed")

    # Non-blocking expiry warning — shown after main window is visible
    days_left = get_days_until_expiry(result)
    if result.valid and days_left < 14:
        import ui.popups.msgbox as _msgbox
        from PySide6.QtCore import QTimer

        def _show_renewal_warning():
            _msgbox.warning(
                window,
                "License Expiring Soon",
                f"Your CleanSheet license expires in <b>{days_left} day{'s' if days_left != 1 else ''}</b>.<br><br>"
                "Please contact <b>support@gd365.com</b> to renew before it expires.",
            )

        QTimer.singleShot(800, _show_renewal_warning)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

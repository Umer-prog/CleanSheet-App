import json
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

import ui.theme as theme
from utils.paths import resource_path, user_data_path


def main() -> None:
    """Entry point: validate license, load branding, launch the app."""
    theme.load(resource_path("branding.json"))

    app = QApplication(sys.argv)

    # Read persisted dark-mode preference before any window is shown
    _cfg_path = user_data_path("app_config.json")
    _dark = True
    try:
        with open(_cfg_path, encoding="utf-8") as _f:
            _dark = json.load(_f).get("dark_mode", True)
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    app.setStyleSheet(theme.DARK_QSS if _dark else theme.LIGHT_QSS)

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

    # Non-blocking expiry warning — shown after main window is visible
    days_left = get_days_until_expiry(result)
    if result.valid and days_left < 14:
        def _show_renewal_warning():
            msg = QMessageBox(window)
            msg.setWindowTitle("License Expiring Soon")
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText(
                f"Your CleanSheet license expires in {days_left} day{'s' if days_left != 1 else ''}.\n"
                "Please contact support@gd365.com to renew."
            )
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()

        from PySide6.QtCore import QTimer
        QTimer.singleShot(800, _show_renewal_warning)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

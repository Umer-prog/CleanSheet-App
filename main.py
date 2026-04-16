import sys

from PySide6.QtWidgets import QApplication

import ui.theme as theme
from utils.paths import resource_path, user_data_path


def main() -> None:
    """Entry point: load branding, apply QSS, launch the app."""
    theme.load(resource_path("branding.json"))

    app = QApplication(sys.argv)

    # Read persisted dark-mode preference before any window is shown
    import json
    _cfg_path = user_data_path("app_config.json")
    _dark = True
    try:
        with open(_cfg_path, encoding="utf-8") as _f:
            _dark = json.load(_f).get("dark_mode", True)
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    app.setStyleSheet(theme.DARK_QSS if _dark else theme.LIGHT_QSS)

    from ui.app import App
    window = App()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

import ui.theme as theme


def main() -> None:
    """Entry point: load branding, apply QSS, launch the app."""
    theme.load(Path(__file__).parent / "branding.json")

    app = QApplication(sys.argv)
    app.setStyleSheet(theme.QSS)

    from ui.app import App
    window = App()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

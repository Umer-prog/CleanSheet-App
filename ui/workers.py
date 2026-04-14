"""Shared threading and loading overlay utilities for all UI screens and views."""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QProgressBar, QWidget


class Worker(QThread):
    """Generic background worker.  Emits finished(result) or errored(exc)."""

    finished = Signal(object)
    errored = Signal(object)

    def __init__(self, fn):
        super().__init__()
        self._fn = fn

    def run(self) -> None:
        try:
            self.finished.emit(self._fn())
        except Exception as exc:  # noqa: BLE001
            self.errored.emit(exc)


class LoadingOverlay(QFrame):
    """Full-widget translucent loading overlay with an indeterminate progress bar.

    Create as a child of the target widget, then call show_on() / hide() as needed.
    """

    def __init__(self, parent: QWidget, message: str = "Loading..."):
        super().__init__(parent)
        self.setStyleSheet(
            "LoadingOverlay { background-color: rgba(15,17,23,0.88); }"
        )
        self.hide()

        card = QFrame(self)
        card.setFixedWidth(280)
        card.setStyleSheet("QFrame { background-color: #13161e; border-radius: 12px; }")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 18, 24, 18)
        card_layout.setSpacing(10)

        lbl = QLabel(message)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(
            "color: #f1f5f9; font-size: 14px; font-weight: bold; background: transparent;"
        )
        card_layout.addWidget(lbl)

        bar = QProgressBar()
        bar.setRange(0, 0)  # indeterminate animation
        bar.setFixedHeight(4)
        bar.setTextVisible(False)
        card_layout.addWidget(bar)

        self._card = card
        card.adjustSize()

    def show_on(self) -> None:
        """Show overlay covering the parent widget."""
        p = self.parent()
        if p:
            self.setGeometry(p.rect())
        self._center_card()
        self.raise_()
        self.show()

    def _center_card(self) -> None:
        self._card.move(
            max(0, (self.width() - self._card.width()) // 2),
            max(0, (self.height() - self._card.height()) // 2),
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._center_card()


class ScreenBase(QWidget):
    """Base class for all screens and views that need background task support."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._workers: list[Worker] = []
        self._loading_count: int = 0
        self._overlay: LoadingOverlay | None = None

    def _setup_overlay(self, message: str = "Loading...") -> None:
        """Build and attach the loading overlay.  Call once in __init__."""
        self._overlay = LoadingOverlay(self, message)

    def _run_background(self, fn, on_success=None, on_error=None) -> None:
        """Run *fn* in a background QThread.  Results are delivered on the main thread."""
        self._loading_count += 1
        if self._loading_count == 1 and self._overlay:
            self._overlay.show_on()

        worker = Worker(fn)
        self._workers.append(worker)

        def _done(result):
            if worker in self._workers:
                self._workers.remove(worker)
            self._loading_count = max(0, self._loading_count - 1)
            if self._loading_count == 0 and self._overlay:
                self._overlay.hide()
            if on_success:
                on_success(result)

        def _fail(exc):
            if worker in self._workers:
                self._workers.remove(worker)
            self._loading_count = max(0, self._loading_count - 1)
            if self._loading_count == 0 and self._overlay:
                self._overlay.hide()
            if on_error:
                on_error(exc)
            else:
                self._set_error(str(exc))

        worker.finished.connect(_done)
        worker.errored.connect(_fail)
        worker.start()

    def _set_error(self, msg: str) -> None:
        """Override in subclasses to show inline error messages."""

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._overlay and self._overlay.isVisible():
            self._overlay.setGeometry(self.rect())


def clear_layout(layout) -> None:
    """Remove and delete all widgets from a layout."""
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w:
            w.deleteLater()


def make_scroll_area(parent=None):
    """Return (QScrollArea, container_widget, container_QVBoxLayout) aligned to top."""
    from PySide6.QtWidgets import QScrollArea
    from PySide6.QtCore import Qt

    scroll = QScrollArea(parent)
    scroll.setWidgetResizable(True)
    scroll.setFrameStyle(QFrame.NoFrame)
    scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

    container = QWidget()
    container.setStyleSheet("background: transparent;")
    layout = QVBoxLayout(container)
    layout.setAlignment(Qt.AlignTop)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    scroll.setWidget(container)
    return scroll, container, layout

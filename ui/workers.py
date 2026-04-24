"""Shared threading and loading overlay utilities for all UI screens and views."""
from __future__ import annotations

import queue as _queue
import threading

from PySide6.QtCore import QObject, QTimer, Signal, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QProgressBar, QWidget


class Worker(QObject):
    """
    Background worker using threading.Thread + QTimer polling.

    Why not QThread: heavy Python work (pandas loops, CSV parsing) holds the
    GIL and starves the main thread's event loop, freezing progress-bar
    animations.  By running work in a plain threading.Thread and polling for
    the result with a QTimer, the event loop gets a slot every _POLL_MS
    milliseconds regardless of what the background thread is doing.

    API is identical to the old QThread-based Worker:
      worker.finished  — Signal(object), emitted on the main thread
      worker.errored   — Signal(object), emitted on the main thread
      worker.start()   — kick off background work
    """

    finished = Signal(object)
    errored  = Signal(object)

    _POLL_MS = 30  # check for a result every 30 ms (~33 fps headroom)

    def __init__(self, fn):
        super().__init__()
        self._fn     = fn
        self._queue  = _queue.SimpleQueue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._timer  = QTimer(self)
        self._timer.setInterval(self._POLL_MS)
        self._timer.timeout.connect(self._poll)

    def start(self) -> None:
        self._timer.start()
        self._thread.start()

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _run(self) -> None:
        """Executes on the background thread — must never touch Qt widgets."""
        try:
            self._queue.put(("ok", self._fn()))
        except Exception as exc:  # noqa: BLE001
            self._queue.put(("err", exc))

    def _poll(self) -> None:
        """Called on the main thread every _POLL_MS ms by the QTimer."""
        try:
            tag, value = self._queue.get_nowait()
        except _queue.Empty:
            return
        self._timer.stop()
        if tag == "ok":
            self.finished.emit(value)
        else:
            self.errored.emit(value)


class ProgressWorker(QObject):
    """
    Background worker that can emit per-step progress updates.

    The wrapped function must accept a single positional argument: a callable
    ``report_progress(done: int, total: int)`` that can be called from the
    background thread to push progress events to the main thread.

    Signals:
        finished(object)    — result value returned by fn
        errored(object)     — exception raised by fn
        progress(int, int)  — (done, total) emitted each time report_progress is called
    """

    finished = Signal(object)
    errored  = Signal(object)
    progress = Signal(int, int)

    _POLL_MS = 30

    def __init__(self, fn):
        super().__init__()
        self._fn              = fn
        self._result_queue    = _queue.SimpleQueue()
        self._progress_queue  = _queue.SimpleQueue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._timer  = QTimer(self)
        self._timer.setInterval(self._POLL_MS)
        self._timer.timeout.connect(self._poll)

    def start(self) -> None:
        self._timer.start()
        self._thread.start()

    def _report_progress(self, done: int, total: int) -> None:
        self._progress_queue.put((done, total))

    def _run(self) -> None:
        try:
            self._result_queue.put(("ok", self._fn(self._report_progress)))
        except Exception as exc:  # noqa: BLE001
            self._result_queue.put(("err", exc))

    def _poll(self) -> None:
        while True:
            try:
                done, total = self._progress_queue.get_nowait()
                self.progress.emit(done, total)
            except _queue.Empty:
                break

        try:
            tag, value = self._result_queue.get_nowait()
        except _queue.Empty:
            return
        self._timer.stop()
        if tag == "ok":
            self.finished.emit(value)
        else:
            self.errored.emit(value)


class LoadingOverlay(QFrame):
    """Full-widget translucent loading overlay with a timer-driven dot animation.

    Uses an explicit QTimer (not QProgressBar) so the animation is never
    gated on Qt's style engine or paint-event delivery — it ticks reliably
    even when heavy background work holds the GIL.

    Create as a child of the target widget, then call show_on() / hide().
    """

    # Four-step dot pulse: one lit dot sweeps left→right
    _FRAMES = ["●  ·  ·", "·  ●  ·", "·  ·  ●", "·  ●  ·"]
    _TICK_MS = 220   # animation frame interval

    def __init__(self, parent: QWidget, message: str = "Loading..."):
        super().__init__(parent)
        self.setStyleSheet(
            "LoadingOverlay { background-color: rgba(15,17,23,0.88); }"
        )

        card = QFrame(self)
        card.setFixedWidth(240)
        card.setStyleSheet("QFrame { background-color: #13161e; border-radius: 12px; }")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(12)

        self._msg_lbl = QLabel(message)
        self._msg_lbl.setAlignment(Qt.AlignCenter)
        self._msg_lbl.setStyleSheet(
            "color: #94a3b8; font-size: 13px; background: transparent;"
        )
        card_layout.addWidget(self._msg_lbl)

        # Dot animation row
        dot_row = QHBoxLayout()
        dot_row.setContentsMargins(0, 0, 0, 0)
        self._dot_lbl = QLabel(self._FRAMES[0])
        self._dot_lbl.setAlignment(Qt.AlignCenter)
        self._dot_lbl.setStyleSheet(
            "color: #3b82f6; font-size: 16px; letter-spacing: 4px; "
            "background: transparent;"
        )
        dot_row.addWidget(self._dot_lbl)
        card_layout.addLayout(dot_row)

        # Progress bar (hidden until update_progress() is called)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(6)
        self._progress_bar.setStyleSheet(
            "QProgressBar { background: #1e2330; border-radius: 3px; border: none; }"
            "QProgressBar::chunk { background: #3b82f6; border-radius: 3px; }"
        )
        self._progress_bar.hide()
        card_layout.addWidget(self._progress_bar)

        self._card = card
        self._frame_idx = 0
        card.adjustSize()

        # Self-contained animation timer — independent of style/paint system
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(self._TICK_MS)
        self._anim_timer.timeout.connect(self._tick)

        self.hide()  # must come after _anim_timer is assigned

    def show_on(self) -> None:
        """Show overlay covering the parent widget and start dot animation."""
        p = self.parent()
        if p:
            self.setGeometry(p.rect())
        self._center_card()
        self.raise_()
        self.show()
        self._frame_idx = 0
        self._dot_lbl.setText(self._FRAMES[0])
        self._dot_lbl.show()
        self._progress_bar.hide()
        self._progress_bar.setValue(0)
        self._anim_timer.start()

    def update_progress(self, done: int, total: int, message: str = "") -> None:
        """Switch to progress-bar mode and update the bar value and message."""
        self._anim_timer.stop()
        self._dot_lbl.hide()
        self._progress_bar.show()
        if total > 0:
            self._progress_bar.setValue(int(done / total * 100))
        if message:
            self._msg_lbl.setText(message)
        self._card.adjustSize()
        self._center_card()

    def hide(self) -> None:
        """Hide overlay and stop animation timer."""
        self._anim_timer.stop()
        super().hide()

    def _tick(self) -> None:
        self._frame_idx = (self._frame_idx + 1) % len(self._FRAMES)
        self._dot_lbl.setText(self._FRAMES[self._frame_idx])

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
        """Run *fn* in a background thread.  Results are delivered on the main thread."""
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

    def _run_background_with_progress(
        self,
        fn,
        on_progress=None,
        on_success=None,
        on_error=None,
    ) -> None:
        """Run *fn(report_progress)* in background with per-step progress signals.

        *fn* receives a callable ``report_progress(done, total)`` it can call
        from the background thread.  *on_progress(done, total)* is called on
        the main thread after each report.
        """
        self._loading_count += 1
        if self._loading_count == 1 and self._overlay:
            self._overlay.show_on()

        worker = ProgressWorker(fn)
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

        def _progress(done, total):
            if on_progress:
                on_progress(done, total)

        worker.finished.connect(_done)
        worker.errored.connect(_fail)
        worker.progress.connect(_progress)
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

# CleanSheet — PySide6 Migration Brief

## Context
CleanSheet is a desktop data mapping application currently built with CustomTkinter.
We are migrating the UI layer to PySide6. This is a UI-only migration — all data
processing, file I/O, and business logic is unchanged.

---

## What is NOT changing
- All pandas / openpyxl / data processing logic
- Project save/load logic
- PyInstaller build setup
- `resource_path()` / `sys._MEIPASS` helper for packaged file paths
- Any existing Python packages or modules below the UI layer

Do not touch these. Only rewrite UI code.

---

## What IS changing
- All `customtkinter` imports → PySide6 equivalents
- All `CTk*` widgets → `Q*` widgets
- `app.mainloop()` → `QApplication.exec()`
- `.command=` callbacks → `.clicked.connect(handler)` signals
- Manual scrollable frames with rows → `QTableView` + `QAbstractTableModel`
- Manual threading hacks → `QThread` + signals/slots

---

## Target window
- Fixed size: **1280 × 720px**
- No resize. Use: `window.setFixedSize(1280, 720)`
- No native title bar decorations needed beyond default

---

## Layout structure
```
QMainWindow (1280x720)
├── QWidget (central)
│   └── QHBoxLayout
│       ├── Sidebar QFrame (fixed width: 260px)
│       │   ├── Brand header (logo + name + subtitle)
│       │   ├── Search QLineEdit
│       │   ├── Section label
│       │   ├── Project list QListWidget
│       │   └── Footer QPushButton ("New Project")
│       └── Main QFrame (flex: remaining width)
│           ├── Topbar QFrame (fixed height: 64px)
│           │   ├── Left: project title QLabel + meta QLabel
│           │   └── Right: action QPushButtons (Duplicate, Open, Delete)
│           ├── Stats strip QFrame (fixed height: 96px)
│           │   └── QHBoxLayout with 4 stat cards
│           ├── Content QFrame (flex: remaining height)
│           │   ├── Project panel QFrame (fixed width: 380px)
│           │   │   └── QTableView (pandas model)
│           │   └── Detail panel QFrame (flex: remaining)
│           │       └── Detail cards (name, client, last modified, actions)
│           └── Status bar QFrame (fixed height: 36px)
```

---

## QTableView + pandas model pattern
For any table that loads from a DataFrame, always use this pattern.
Never use QTableWidget — it renders all rows eagerly and will lag on large files.

```python
from PySide6.QtCore import QAbstractTableModel, Qt
import pandas as pd

class PandasModel(QAbstractTableModel):
    def __init__(self, df: pd.DataFrame):
        super().__init__()
        self._df = df

    def rowCount(self, parent=None):
        return len(self._df)

    def columnCount(self, parent=None):
        return len(self._df.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            return str(self._df.iloc[index.row(), index.column()])
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._df.columns[section])
            return str(section + 1)
        return None
```

Attach to a view like:
```python
self.table_view = QTableView()
self.model = PandasModel(df)
self.table_view.setModel(self.model)
```

---

## Threading pattern
Any file loading or heavy processing must run off the UI thread.
Always use this pattern — never block the main thread directly.

```python
from PySide6.QtCore import QThread, Signal

class FileWorker(QThread):
    finished = Signal(object)   # emits the result (e.g. a DataFrame)
    error = Signal(str)         # emits error message string

    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath

    def run(self):
        try:
            df = pd.read_excel(self.filepath)  # or read_csv etc.
            self.finished.emit(df)
        except Exception as e:
            self.error.emit(str(e))

# Usage in a widget:
self.worker = FileWorker(path)
self.worker.finished.connect(self.on_file_loaded)
self.worker.error.connect(self.on_file_error)
self.worker.start()
```

Keep a reference to the worker on `self` — if it goes out of scope Python will
garbage-collect it mid-run and you will get a silent crash.

---

## Styling (QSS dark theme)
Apply a single QSS stylesheet to `QApplication` at startup.
Do not set styles widget-by-widget unless overriding a specific instance.

### Color tokens
```
Background primary:   #0f1117
Background surface:   #13161e
Border:               rgba(255,255,255,0.07)
Text primary:         #f1f5f9
Text secondary:       #94a3b8
Text muted:           #475569
Accent blue:          #3b82f6
Accent blue hover:    #2563eb
Danger:               #f87171
Danger bg:            rgba(239,68,68,0.07)
```

### QSS skeleton
```python
QSS = """
QMainWindow, QWidget {
    background-color: #0f1117;
    color: #f1f5f9;
    font-family: 'Segoe UI';
    font-size: 13px;
}
QFrame#sidebar {
    background-color: #13161e;
    border-right: 1px solid rgba(255,255,255,0.07);
}
QFrame#topbar {
    background-color: #13161e;
    border-bottom: 1px solid rgba(255,255,255,0.07);
}
QLineEdit {
    background-color: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 7px;
    padding: 4px 10px;
    color: #94a3b8;
}
QPushButton#btn_primary {
    background-color: #3b82f6;
    border: none;
    border-radius: 7px;
    color: white;
    padding: 6px 16px;
    font-weight: 600;
}
QPushButton#btn_primary:hover { background-color: #2563eb; }
QPushButton#btn_ghost {
    background-color: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 7px;
    color: #94a3b8;
    padding: 6px 14px;
}
QPushButton#btn_ghost:hover { background-color: rgba(255,255,255,0.07); }
QPushButton#btn_danger {
    background-color: rgba(239,68,68,0.07);
    border: 1px solid rgba(239,68,68,0.2);
    border-radius: 7px;
    color: #f87171;
    padding: 6px 14px;
}
QPushButton#btn_danger:hover { background-color: rgba(239,68,68,0.13); }
QTableView {
    background-color: transparent;
    border: none;
    gridline-color: rgba(255,255,255,0.04);
    selection-background-color: rgba(59,130,246,0.12);
    selection-color: #93c5fd;
}
QTableView::item { padding: 8px 12px; border-bottom: 1px solid rgba(255,255,255,0.04); }
QHeaderView::section {
    background-color: #13161e;
    color: #475569;
    font-size: 11px;
    padding: 6px 12px;
    border: none;
    border-bottom: 1px solid rgba(255,255,255,0.07);
    text-transform: uppercase;
    letter-spacing: 1px;
}
QScrollBar:vertical { background: transparent; width: 6px; }
QScrollBar::handle:vertical { background: rgba(255,255,255,0.08); border-radius: 3px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QListWidget { background: transparent; border: none; }
QListWidget::item { padding: 10px 18px; border-left: 2px solid transparent; color: #94a3b8; }
QListWidget::item:selected { background: rgba(59,130,246,0.1); border-left-color: #3b82f6; color: #93c5fd; }
QListWidget::item:hover { background: rgba(255,255,255,0.03); }
"""

app = QApplication(sys.argv)
app.setStyleSheet(QSS)
```

---

## Naming conventions for objectName (used in QSS targeting)
| Widget | objectName |
|--------|-----------|
| Sidebar frame | `sidebar` |
| Topbar frame | `topbar` |
| Stats strip | `stats_strip` |
| Status bar | `status_bar` |
| Primary button | `btn_primary` |
| Ghost button | `btn_ghost` |
| Danger button | `btn_danger` |
| Project list | `project_list` |
| Main table view | `main_table` |

Set with: `widget.setObjectName("name")`

---

## PyInstaller — unchanged rules
- Entry point: same as before
- `resource_path()` helper: unchanged
- Hidden imports to add for PySide6:
  ```
  --hidden-import PySide6.QtCore
  --hidden-import PySide6.QtWidgets
  --hidden-import PySide6.QtGui
  ```
- Or add to `.spec` file `hiddenimports` list

---

## What to build first (suggested order)
1. `main.py` — QApplication init, QSS applied, MainWindow shown
2. `main_window.py` — top-level layout, sidebar + main split
3. `sidebar.py` — brand, search, project list, new button
4. `project_table.py` — QTableView + PandasModel
5. `detail_panel.py` — selected project info + action buttons
6. `workers.py` — FileWorker QThread for all file loading
7. Wire everything together with signals/slots

---

## Things Claude Code must NOT do
- Do not use `QTableWidget` — use `QTableView` + model only
- Do not load files on the main thread — always use FileWorker
- Do not set widget colors inline with `setStyleSheet` per-widget unless
  overriding a specific instance — use the global QSS
- Do not use `.exec_()` — PySide6 uses `.exec()` (no underscore)
- Do not import from `PyQt6` — we are using `PySide6` exclusively
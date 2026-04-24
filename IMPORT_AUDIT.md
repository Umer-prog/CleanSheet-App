# IMPORT_AUDIT.md — CleanSheet Import Audit

Generated as part of Section 1 of the Performance Optimization Plan.
No source files were modified. This document is view-only.

---

## Third-Party Packages

| Package | Submodule / Class / Function | Files That Import It |
|---------|------------------------------|----------------------|
| **pandas** | `pd.DataFrame`, `pd.read_csv`, `pd.read_excel`, `pd.ExcelWriter`, `pd.ExcelFile`, `pd.concat`, `pd.Series` | `core/data_loader.py`, `core/dim_manager.py`, `core/final_export_manager.py`, `core/error_detector.py`, `core/snapshot_manager.py`, `core/chain_writer.py`, `ui/screen2_mappings.py`, `ui/popups/popup_add.py`, `ui/popups/popup_replace.py`, `ui/views/view_mapping.py`, `tests/test_*.py` |
| **PySide6.QtCore** | `Qt`, `QObject`, `QPoint`, `QTimer`, `Signal`, `QAbstractTableModel`, `QModelIndex`, `QSortFilterProxyModel` | `ui/theme.py`, `ui/app.py`, `ui/workers.py`, `ui/screen0_launcher.py`, `ui/screen1_sources.py`, `ui/screen2_mappings.py`, `ui/screen3_main.py`, `ui/screen15_chain_mapper.py`, `ui/popups/msgbox.py`, `ui/popups/popup_add.py`, `ui/popups/popup_replace.py`, `ui/popups/popup_revert_confirm.py`, `ui/popups/popup_sheet_selector.py`, `ui/popups/popup_single_sheet.py`, `ui/views/view_mapping.py`, `ui/views/view_history.py`, `ui/views/view_settings.py`, `ui/views/view_t_sources.py`, `ui/views/view_d_sources.py` |
| **PySide6.QtGui** | `QFont`, `QColor`, `QPainter`, `QPixmap`, `QBrush`, `QPalette` | `ui/theme.py`, `ui/screen0_launcher.py`, `ui/views/view_mapping.py` |
| **PySide6.QtWidgets** | `QApplication`, `QMainWindow`, `QWidget`, `QFrame`, `QHBoxLayout`, `QVBoxLayout`, `QLabel`, `QPushButton`, `QLineEdit`, `QMessageBox`, `QFileDialog`, `QScrollArea`, `QTableView`, `QHeaderView`, `QSizePolicy`, `QStyledItemDelegate`, `QAbstractItemView`, `QDialog`, `QComboBox`, `QCheckBox`, `QTextEdit`, `QSpinBox`, `QGraphicsOpacityEffect` | All `ui/` files |
| **openpyxl** | `openpyxl.load_workbook()` | `core/data_loader.py`, `ui/popups/popup_sheet_selector.py` |
| **pytest** | `pytest.fixture`, `pytest.mark`, `pytest.raises` | `tests/test_project_manager.py`, `tests/test_snapshot_manager.py`, `tests/test_mapping_manager.py`, `tests/test_error_detector.py`, `tests/test_screen1_sources.py`, `tests/test_screen2_mappings.py`, `tests/test_screen3_main.py`, `tests/test_view_mapping.py`, `tests/test_sources_views.py`, `tests/test_section10_views.py`, `tests/test_final_export_manager.py` |

### PySide6 Submodule Summary (for PyInstaller hiddenimports)

Only three Qt submodules are used across the entire codebase:

| Submodule | Used |
|-----------|------|
| `PySide6.QtCore` | Yes |
| `PySide6.QtGui` | Yes |
| `PySide6.QtWidgets` | Yes |
| `PySide6.QtNetwork` | No |
| `PySide6.QtSql` | No |
| `PySide6.QtMultimedia` | No |
| `PySide6.QtOpenGL` | No |
| `PySide6.QtSvg` | No |
| `PySide6.QtXml` | No |
| `PySide6.QtPrintSupport` | No |
| `PySide6.QtBluetooth` | No |
| `PySide6.QtWebEngineWidgets` | No |

---

## Standard Library Modules

| Module | Symbols Used | Files |
|--------|--------------|-------|
| `__future__` | `annotations` | Most `core/` and `ui/` files |
| `datetime` | `date`, `datetime` | `core/project_manager.py`, `core/snapshot_manager.py`, `core/data_loader.py`, `ui/screen0_launcher.py` |
| `difflib` | `SequenceMatcher` | `ui/screen15_chain_mapper.py` |
| `hashlib` | `md5` | `core/snapshot_manager.py` |
| `json` | `json.loads`, `json.dumps`, `json.load`, `json.dump` | `core/project_manager.py`, `core/mapping_manager.py`, `core/project_paths.py`, `core/data_loader.py`, `core/snapshot_manager.py`, `ui/app.py`, `ui/theme.py`, `main.py`, `tests/` |
| `pathlib` | `Path` | All `core/`, `ui/`, `utils/`, `tests/` files |
| `queue` | `SimpleQueue` (imported as `_queue`) | `ui/workers.py` |
| `re` | `re.sub`, `re.compile`, `re.IGNORECASE` | `core/data_loader.py`, `ui/screen1_sources.py`, `ui/popups/popup_add.py` |
| `shutil` | `shutil.copy`, `shutil.rmtree`, `shutil.copytree` | `core/snapshot_manager.py`, `ui/screen0_launcher.py` |
| `sys` | `sys.argv`, `sys.exit`, `sys._MEIPASS` | `utils/paths.py`, `main.py` |
| `tempfile` | `tempfile.gettempdir()`, `tempfile.mkdtemp()` | `ui/screen2_mappings.py`, `ui/screen15_chain_mapper.py`, `ui/popups/popup_single_sheet.py` |
| `threading` | `Thread` | `ui/workers.py` |
| `typing` | `Callable` | `ui/popups/popup_add.py`, `ui/popups/popup_replace.py`, `ui/views/view_mapping.py`, `ui/views/view_t_sources.py`, `ui/views/view_d_sources.py` |

---

## Suspicious or Potentially Unused Imports

| File | Import | Issue |
|------|--------|-------|
| `core/data_loader.py` | `import pandas as pd` (inside function bodies) | Pandas is already imported at module level. The redundant local re-imports inside `_write_dimensions()` and `_load_dim_tables_from_dir()` are harmless but unnecessary. Should be removed. |
| `ui/theme.py` | `from PySide6.QtWidgets import QApplication` (inside `apply_theme()`) | QApplication is already imported at module level in `theme.py`. The in-function re-import is redundant. |
| `ui/theme.py` | `__import__("PySide6.QtCore", fromlist=["Qt"])` | Dynamic runtime import instead of a standard static `from PySide6.QtCore import Qt` at module level. Poor practice; should be converted to a static import. |

---

## Minimum pip Requirements for Production Build

```
pandas
PySide6
openpyxl
```

`pytest` is a dev/test dependency only and must **not** be included in the production virtual environment or the PyInstaller build.

---

## Notes

- The app uses no database layer (no `sqlite3`, no `sqlalchemy`).
- No network requests are made (`requests`, `httpx`, `urllib` not used).
- No `tkinter` dependency despite the app originally being designed for CustomTkinter — the current codebase has fully migrated to PySide6.
- `rapidfuzz` is mentioned in `CLAUDE.md` as available but is **not imported anywhere** in the current codebase.
- `xlsxwriter` is **not currently used** — the final export uses openpyxl via pandas' default engine. Section 6 of the optimization plan will add it.
- Only three PySide6 submodules are needed: `QtCore`, `QtGui`, `QtWidgets`. All other Qt modules can be excluded from the PyInstaller build.

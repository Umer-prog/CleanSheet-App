# IMPORT_AUDIT.md — CleanSheet Import Audit

Updated: 2026-05-02  
No source files were modified. This document is view-only.

---

## 1. Third-Party Packages

### 1.1 `pandas`

| Symbols Used | Files |
|---|---|
| `pd` (full namespace) — `DataFrame`, `read_csv`, `read_excel`, `ExcelWriter`, `ExcelFile`, `concat`, `Series` | `core/data_loader.py`, `core/dim_manager.py`, `core/final_export_manager.py`, `core/error_detector.py`, `core/snapshot_manager.py`, `core/chain_writer.py`, `ui/screen2_mappings.py`, `ui/popups/popup_add.py`, `ui/popups/popup_replace.py`, `ui/views/view_mapping.py` |

**EXE note:** Must be in `hiddenimports`. Several internal Cython extensions (`_libs.tslibs.*`) are not auto-detected by PyInstaller — see Section 4 spec list.

---

### 1.2 `PySide6`

Only three Qt submodules are imported across the entire codebase.

#### `PySide6.QtCore`

| Symbols | Files |
|---|---|
| `Qt` | Nearly all `ui/` files |
| `QObject` | `ui/workers.py` |
| `QPoint` | `ui/app.py` |
| `QTimer` | `ui/app.py`, `ui/activation_screen.py`, `ui/popups/msgbox.py`, `ui/popups/popup_replace.py`, `ui/views/view_d_sources.py` |
| `Signal` | `ui/workers.py` |
| `QAbstractTableModel`, `QModelIndex` | `ui/popups/popup_replace.py`, `ui/views/view_mapping.py` |
| `QSortFilterProxyModel` | Listed in old audit — **not found in current source. Likely removed.** |

#### `PySide6.QtGui`

| Symbols | Files |
|---|---|
| `QFont` | `ui/theme.py`, `ui/activation_screen.py` |
| `QColor` | `ui/screen0_launcher.py`, `ui/views/view_mapping.py` |
| `QPainter` | `ui/screen0_launcher.py` |
| `QPixmap` | `ui/screen0_launcher.py` |
| `QBrush` | `ui/views/view_mapping.py` |
| `QPalette` | `ui/views/view_mapping.py` |
| `QCloseEvent` | `ui/app.py` |

#### `PySide6.QtWidgets`

| Symbols | Files |
|---|---|
| `QApplication` | `ui/app.py`, `ui/activation_screen.py`, `ui/popups/msgbox.py`, `main.py` |
| `QMainWindow` | `ui/app.py` |
| `QWidget` | All `ui/` files |
| `QFrame` | All `ui/` files |
| `QHBoxLayout`, `QVBoxLayout` | All `ui/` files |
| `QGridLayout` | `ui/popups/popup_add.py` |
| `QLabel` | All `ui/` files |
| `QPushButton` | All `ui/` files |
| `QLineEdit` | `ui/activation_screen.py`, `ui/screen2_mappings.py` (indirectly), `ui/popups/popup_add.py`, `ui/popups/popup_replace.py`, `ui/views/view_d_sources.py`, `ui/views/view_settings.py`, `ui/views/view_history.py` |
| `QFileDialog` | `ui/activation_screen.py`, `ui/screen0_launcher.py`, `ui/screen1_sources.py`, `ui/screen15_chain_mapper.py`, `ui/views/view_t_sources.py`, `ui/views/view_d_sources.py` |
| `QScrollArea` | `ui/screen0_launcher.py`, `ui/screen1_sources.py`, `ui/screen2_mappings.py`, `ui/screen15_chain_mapper.py`, `ui/popups/popup_add.py`, `ui/popups/popup_replace.py`, `ui/popups/popup_sheet_selector.py`, `ui/views/view_mapping.py`, `ui/views/view_t_sources.py`, `ui/views/view_d_sources.py`, `ui/views/view_settings.py`, `ui/views/view_history.py` |
| `QTableView` | `ui/popups/popup_replace.py`, `ui/views/view_mapping.py` |
| `QHeaderView` | `ui/views/view_mapping.py` |
| `QSizePolicy` | `ui/views/view_mapping.py` |
| `QStyledItemDelegate` | `ui/views/view_mapping.py` |
| `QAbstractItemView` | `ui/popups/popup_replace.py`, `ui/views/view_mapping.py` |
| `QDialog` | `ui/activation_screen.py`, `ui/popups/msgbox.py`, `ui/popups/popup_add.py`, `ui/popups/popup_replace.py`, `ui/popups/popup_revert_confirm.py`, `ui/popups/popup_sheet_selector.py`, `ui/popups/popup_single_sheet.py`, `ui/popups/popup_about.py`, `ui/views/view_history.py` |
| `QCheckBox` | `ui/views/view_settings.py` |
| `QTextEdit` | `ui/popups/msgbox.py`, `ui/views/view_history.py` |
| `QSpinBox` | `ui/popups/popup_sheet_selector.py`, `ui/popups/popup_single_sheet.py` |
| `QProgressBar` | `ui/workers.py` |
| `QGraphicsOpacityEffect` | `ui/popups/popup_sheet_selector.py` |
| `QComboBox` | `ui/widgets.py` (subclassed as `NoScrollComboBox`) |
| `QSizePolicy` | `ui/views/view_mapping.py` |
| `QMessageBox` | **Not used** — replaced entirely by custom `ui/popups/msgbox.py` |

#### PySide6 submodule summary (for PyInstaller)

| Submodule | Used | Required in hiddenimports |
|---|---|---|
| `PySide6.QtCore` | Yes | Yes |
| `PySide6.QtGui` | Yes | Yes |
| `PySide6.QtWidgets` | Yes | Yes |
| `PySide6.QtSvg` | **No direct import** — but SVG assets used; Qt may load it at runtime | **Yes — include as hidden import** |
| `PySide6.QtNetwork` | No | No |
| `PySide6.QtSql` | No | No |
| `PySide6.QtMultimedia` | No | Exclude explicitly |
| `PySide6.QtOpenGL` | No | No |
| `PySide6.QtXml` | No | No |
| `PySide6.QtPrintSupport` | No | No |
| `PySide6.QtBluetooth` | No | Exclude explicitly |
| `PySide6.QtWebEngineWidgets` | No | Exclude explicitly |
| `PySide6.Qt3DCore` | No | Exclude explicitly |
| `PySide6.QtLocation` | No | Exclude explicitly |

---

### 1.3 `openpyxl`

| Symbols | Files |
|---|---|
| `openpyxl.load_workbook()` | `core/data_loader.py`, `ui/popups/popup_sheet_selector.py` |

**EXE note:** Must be in `hiddenimports`. Add `openpyxl.cell._writer` and `openpyxl.styles.stylesheet` — these are lazy-loaded internal modules PyInstaller will miss.

---

### 1.4 `cryptography` ⚠️ NEW — not in previous audit

Used exclusively by the license system.

| Symbols | File |
|---|---|
| `cryptography.exceptions.InvalidSignature` | `core/license_validator.py` |
| `cryptography.hazmat.primitives.hashes` | `core/license_validator.py`, `tools/generate_license.py` |
| `cryptography.hazmat.primitives.serialization` | `core/license_validator.py`, `tools/generate_keys.py`, `tools/generate_license.py` |
| `cryptography.hazmat.primitives.asymmetric.padding` | `core/license_validator.py`, `tools/generate_license.py` |
| `cryptography.hazmat.primitives.asymmetric.rsa` | `tools/generate_keys.py` |

**EXE note:** `cryptography` uses compiled Rust/C extensions. PyInstaller requires `collect_dynamic_libs('cryptography')` or the `hook-cryptography.py` hook. Without it the exe will crash at license validation with `ImportError: cannot import name 'backend'`. Add to `hiddenimports`:
```
'cryptography',
'cryptography.hazmat.backends',
'cryptography.hazmat.backends.openssl',
'cryptography.hazmat.backends.openssl.backend',
'cryptography.hazmat.primitives.asymmetric.rsa',
'cryptography.hazmat.primitives.asymmetric.padding',
'cryptography.hazmat.primitives.hashes',
'cryptography.hazmat.primitives.serialization',
'cryptography.exceptions',
```
Or use `collect_all('cryptography')` in the spec file.

---

### 1.5 `pytest` (dev/test only)

| Files |
|---|
| `tests/test_project_manager.py`, `tests/test_snapshot_manager.py`, `tests/test_mapping_manager.py`, `tests/test_error_detector.py`, `tests/test_screen1_sources.py`, `tests/test_screen2_mappings.py`, `tests/test_screen3_main.py`, `tests/test_view_mapping.py`, `tests/test_sources_views.py`, `tests/test_section10_views.py`, `tests/test_final_export_manager.py` |

**EXE note:** Must NOT be included in the production build or virtual environment. Add `'pytest'`, `'unittest'`, `'test'` to `excludes` in the spec.

---

## 2. Standard Library Modules

| Module | Symbols Used | Files |
|---|---|---|
| `__future__` | `annotations` | Most `core/` and `ui/` files |
| `base64` | `b64decode`, `b64encode` | `core/license_validator.py`, `tools/generate_license.py` |
| `dataclasses` | `dataclass`, `field` | `core/license_validator.py` |
| `datetime` | `date`, `datetime` | `core/project_manager.py`, `core/snapshot_manager.py`, `core/data_loader.py`, `core/license_validator.py`, `ui/screen0_launcher.py`, `tools/generate_license.py` |
| `difflib` | `SequenceMatcher` | `ui/screen15_chain_mapper.py` |
| `hashlib` | `md5` | `core/snapshot_manager.py`, `core/machine_id.py` |
| `json` | `loads`, `dumps`, `load`, `dump` | `core/project_manager.py`, `core/mapping_manager.py`, `core/project_paths.py`, `core/data_loader.py`, `core/snapshot_manager.py`, `ui/app.py`, `ui/theme.py`, `main.py` |
| `logging` | `getLogger`, `basicConfig`, `DEBUG`, `INFO`, etc. | `core/app_logger.py`, `core/data_loader.py`, `core/mapping_manager.py`, `core/project_manager.py`, `core/snapshot_manager.py`, `core/license_validator.py`, `core/final_export_manager.py`, `ui/workers.py`, `main.py` |
| `logging.handlers` | `RotatingFileHandler` | `core/app_logger.py` |
| `os` | `os.path`, `os.environ`, `os.getcwd` | `core/app_logger.py`, `core/data_loader.py` |
| `pathlib` | `Path` | All `core/`, `ui/`, `utils/`, `tests/` files |
| `queue` | `SimpleQueue` (imported as `_queue`) | `ui/workers.py` |
| `re` | `re.sub`, `re.compile`, `re.IGNORECASE` | `core/data_loader.py`, `core/project_manager.py`, `ui/screen1_sources.py`, `ui/popups/popup_add.py` |
| `shutil` | `copy`, `rmtree`, `copytree` | `core/snapshot_manager.py`, `ui/screen0_launcher.py`, `ui/activation_screen.py` |
| `subprocess` | `subprocess.Popen`, `subprocess.run` | `core/machine_id.py`, `ui/screen0_launcher.py`, `ui/popups/msgbox.py`, `ui/views/view_settings.py` |
| `sys` | `sys.argv`, `sys.exit`, `sys._MEIPASS` | `utils/paths.py`, `main.py`, `core/license_constants.py`, `tools/generate_license.py` |
| `tempfile` | `gettempdir()`, `mkdtemp()` | `ui/screen2_mappings.py`, `ui/screen15_chain_mapper.py`, `ui/popups/popup_single_sheet.py` |
| `threading` | `Thread` | `ui/workers.py` |
| `typing` | `Callable`, `Optional` | `core/final_export_manager.py`, `core/license_validator.py`, `core/machine_id.py`, `ui/popups/popup_add.py`, `ui/popups/popup_replace.py`, `ui/views/view_mapping.py`, `ui/views/view_t_sources.py`, `ui/views/view_d_sources.py` |
| `uuid` | `uuid.getnode()` | `core/machine_id.py` |
| `winreg` | `OpenKey`, `QueryValueEx`, `HKEY_LOCAL_MACHINE` | `core/machine_id.py` |

**EXE note for `winreg`:** This is a Windows-only stdlib module. It is always available on Windows builds. No special handling needed for PyInstaller. Do not add it to hiddenimports.

**EXE note for `subprocess`:** Used in `msgbox.py` to open the log folder, and in `view_settings.py` to open file paths. On Windows this calls `os.startfile` / `explorer.exe`. No PyInstaller action needed.

**EXE note for `sys._MEIPASS`:** This attribute is set by PyInstaller at runtime on frozen executables. It is the mechanism used by `utils/paths.py → resource_path()` to locate bundled files. This is the correct and intended pattern.

---

## 3. Internal Module Imports

All internal imports use absolute package paths from the project root. No relative imports (`from . import`) are used.

| Importer | Imports From |
|---|---|
| `ui/app.py` | `ui.theme`, `core.constants`, `utils.paths` |
| `ui/activation_screen.py` | `ui.theme`, `core.license_constants`, `core.machine_id`, `core.license_validator` |
| `ui/screen0_launcher.py` | `ui.theme`, `ui.popups.msgbox`, `core.mapping_manager`, `core.project_manager`, `ui.workers` |
| `ui/screen1_sources.py` | `ui.theme`, `ui.popups.msgbox`, `core.data_loader`, `core.project_manager`, `ui.workers` |
| `ui/screen2_mappings.py` | `ui.theme`, `ui.popups.msgbox`, `core.data_loader`, `core.mapping_manager`, `core.project_manager`, `core.project_paths`, `ui.widgets`, `ui.workers` |
| `ui/screen3_main.py` | `ui.theme`, `ui.popups.msgbox`, `core.error_detector`, `core.mapping_manager`, `core.project_manager`, `ui.screen2_mappings`, `ui.workers` |
| `ui/screen15_chain_mapper.py` | `ui.theme`, `ui.widgets`, `core.data_loader`, `ui.workers` |
| `ui/workers.py` | `core.error_messages` |
| `ui/popups/msgbox.py` | `core.app_logger` |
| `ui/popups/popup_about.py` | `core.constants`, `core.app_logger` |
| `ui/popups/popup_replace.py` | `ui.workers` |
| `ui/popups/popup_sheet_selector.py` | `ui.theme`, `core.data_loader` |
| `ui/popups/popup_single_sheet.py` | `ui.theme`, `ui.widgets` |
| `ui/views/view_mapping.py` | `ui.theme`, `ui.popups.msgbox`, `core.data_loader`, `core.dim_manager`, `core.error_detector`, `core.final_export_manager`, `core.project_manager`, `core.project_paths`, `core.snapshot_manager`, `core.mapping_manager`, `ui.workers` |
| `ui/views/view_t_sources.py` | `ui.theme`, `ui.popups.msgbox`, `core.data_loader`, `core.mapping_manager`, `core.project_manager`, `core.project_paths`, `ui.screen1_sources`, `ui.workers` |
| `ui/views/view_d_sources.py` | `ui.theme`, `ui.popups.msgbox`, `core.data_loader`, `core.dim_manager`, `core.mapping_manager`, `core.project_manager`, `core.project_paths`, `ui.screen1_sources`, `ui.workers` |
| `ui/views/view_settings.py` | `ui.theme`, `ui.popups.msgbox`, `core.app_logger`, `core.project_manager`, `ui.workers` |
| `ui/views/view_history.py` | `core.data_loader`, `core.snapshot_manager`, `ui.popups.msgbox`, `ui.workers` |
| `core/chain_writer.py` | `core.data_loader` |
| `core/dim_manager.py` | `core.data_loader`, `core.project_paths` |
| `core/error_detector.py` | `core.dim_manager`, `core.project_paths` |
| `core/final_export_manager.py` | `core.data_loader`, `core.project_manager`, `core.project_paths` |
| `core/license_constants.py` | `core.constants` |
| `core/license_validator.py` | `core.license_constants`, `core.machine_id` |
| `core/mapping_manager.py` | `core.project_paths` |
| `core/snapshot_manager.py` | `core.data_loader`, `core.project_paths` |
| `main.py` | `ui.theme`, `core.app_logger`, `core.constants`, `utils.paths` |
| `tools/generate_keys.py` | *(no internal imports)* |
| `tools/generate_license.py` | *(no internal imports)* |

---

## 4. Suspicious or Unused Imports

| File | Import | Issue |
|---|---|---|
| `core/data_loader.py` | `import pandas as pd` repeated inside function bodies | Pandas is already imported at module level. The redundant local re-imports inside `_write_dimensions()` and `_load_dim_tables_from_dir()` are harmless but unnecessary. |
| `ui/theme.py` | `from PySide6.QtWidgets import QApplication` inside `apply_theme()` | QApplication is already imported at module level. The in-function re-import is redundant. |
| `ui/theme.py` | `__import__("PySide6.QtCore", fromlist=["Qt"])` | Dynamic runtime import instead of `from PySide6.QtCore import Qt` at module level. Should be converted to a static import. |
| `PySide6.QtCore.QSortFilterProxyModel` | Listed in original audit | **No longer found in current source.** Likely removed in a refactor. Remove from hiddenimports if present. |
| `ui/screen15_chain_mapper.py` | `difflib.SequenceMatcher` | This is a legacy/experimental screen. If `screen15_chain_mapper.py` is not part of the production build, `difflib` can be removed from the dependency list. |
| `tools/generate_keys.py`, `tools/generate_license.py` | All imports | These are **developer tooling only** — not bundled in the exe, not deployed to clients. They generate license keys offline. Do not include in PyInstaller build. |

---

## 5. Files NOT Bundled in the EXE

The following files and folders must be excluded from the PyInstaller distribution:

| Path | Reason |
|---|---|
| `tests/` | Dev/test only |
| `tools/` | Key generation tooling — developer only, must never ship to clients |
| `docs/` | Documentation |
| `.claude/` | Claude Code config |
| `*.spec` | Build spec file |
| `requirements*.txt` | Dev dependency lists |
| `branding.json` | **Must be bundled as a data file**, not excluded — include in `datas` |
| `assets/` | **Must be bundled as a data file** — include in `datas` |

---

## 6. Minimum pip Requirements for Production Build

```
pandas
PySide6
openpyxl
cryptography
```

`pytest` is a dev/test dependency only — must **not** be in the production venv or the PyInstaller build.

`tools/generate_keys.py` and `tools/generate_license.py` require `cryptography` as well, but are run in a **separate offline developer environment** and are never bundled.

---

## 7. Complete `hiddenimports` List for `cleansheet.spec`

```python
hiddenimports=[
    # Qt
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtSvg',                        # SVG assets used at runtime

    # openpyxl lazy-loaded internals
    'openpyxl',
    'openpyxl.cell._writer',
    'openpyxl.styles.stylesheet',
    'openpyxl.workbook',

    # pandas Cython extensions
    'pandas',
    'pandas._libs.tslibs.np_datetime',
    'pandas._libs.tslibs.nattype',
    'pandas._libs.tslibs.timedeltas',

    # cryptography (license system)
    'cryptography',
    'cryptography.hazmat.backends',
    'cryptography.hazmat.backends.openssl',
    'cryptography.hazmat.backends.openssl.backend',
    'cryptography.hazmat.primitives.asymmetric.rsa',
    'cryptography.hazmat.primitives.asymmetric.padding',
    'cryptography.hazmat.primitives.hashes',
    'cryptography.hazmat.primitives.serialization',
    'cryptography.exceptions',
],
```

---

## 8. Complete `excludes` List for `cleansheet.spec`

```python
excludes=[
    'PySide6.QtWebEngineWidgets',
    'PySide6.QtMultimedia',
    'PySide6.Qt3DCore',
    'PySide6.QtBluetooth',
    'PySide6.QtLocation',
    'matplotlib',
    'tkinter',
    'pytest',
    'unittest',
    'test',
    'difflib',      # only used in screen15 (legacy screen) — remove if screen15 is excluded
    'tools',
],
```

---

## 9. Notes

- No database layer (`sqlite3`, `sqlalchemy` not used).
- No network requests (`requests`, `httpx`, `urllib` not used anywhere in the app itself).
- `winreg` is used in `core/machine_id.py` to read the Windows machine GUID for license binding. This is Windows-only and is stdlib — no pip package needed.
- `rapidfuzz` is mentioned in `CLAUDE.md` as available but is **not imported anywhere** in the current codebase.
- `xlsxwriter` is **not currently used** — final export uses openpyxl via pandas' default engine.
- `QMessageBox` (Qt's built-in) is **not used** — fully replaced by the custom `ui/popups/msgbox.py` dialog system.
- `CLAUDE.md` references `customtkinter` as the original framework. The codebase has fully migrated to PySide6. There is no `customtkinter` import anywhere.
- `ui/screen15_chain_mapper.py` is a legacy or experimental screen not referenced in the main navigation. Confirm whether it ships in production before finalising the spec.

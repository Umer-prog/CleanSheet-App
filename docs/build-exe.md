# Build CleanSheet EXE

Package the CleanSheet PySide6 app into a standalone Windows executable using PyInstaller.

## Steps

### 1. Audit all file-loading paths in the codebase

Search every file under `core/`, `ui/`, and `main.py` for any code that opens a file by relative path. This includes:
- `open("...")`
- `Path("...")`
- `QPixmap("...")`, `QIcon("...")`
- `json.load`, `pd.read_excel`, `pd.read_csv` — anything that reads from disk using a string or Path literal

For every match found, replace the raw path with a call to a `resource_path()` helper that handles both dev and frozen (PyInstaller) contexts.

Create the helper at `utils/paths.py`:

```python
import sys
from pathlib import Path

def resource_path(relative: str) -> Path:
    """
    Returns the correct absolute path to a bundled resource.
    Works both during development and when frozen by PyInstaller.
    """
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).parent.parent))
    return base / relative
```

Then update every affected call site. Example:

```python
# Before
with open("branding.json") as f:
    ...

# After
from utils.paths import resource_path
with open(resource_path("branding.json")) as f:
    ...
```

Do the same for any icon or image loads in the UI layer, e.g.:

```python
# Before
QIcon("assets/White Color - Icon.svg")

# After
from utils.paths import resource_path
QIcon(str(resource_path("assets/icon.ico")))
```

Note: The `.ico` file will be at `assets/icon.ico` — the user will place it there manually.

---

### 2. Create `utils/__init__.py`

Create an empty `utils/__init__.py` so the new module is importable as a package.

---

### 4. Create `cleansheet.spec`

Create the following file at the project root as `cleansheet.spec`:

```python
# cleansheet.spec
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

pyside6_datas = collect_data_files('PySide6')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('branding.json', '.'),
        *pyside6_datas,
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtSvg',
        'openpyxl',
        'openpyxl.cell._writer',
        'openpyxl.styles.stylesheet',
        'pandas',
        'pandas._libs.tslibs.np_datetime',
        'pandas._libs.tslibs.nattype',
        'pandas._libs.tslibs.timedeltas',
        'pkg_resources.py2_compat',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtMultimedia',
        'PySide6.Qt3DCore',
        'PySide6.QtBluetooth',
        'PySide6.QtLocation',
        'matplotlib',
        'tkinter',
        'test',
        'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CleanSheet',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    icon='assets/icon.ico',
)
```

---

### 5. Run the build

```bash
pyinstaller cleansheet.spec
```

The output will be at `dist/CleanSheet.exe`.

---

### 6. Smoke test

After the build completes, copy `dist/CleanSheet.exe` to a **completely separate folder** (a temp folder with no project files) and launch it. Verify:

- App window opens without error
- Branding/icon displays correctly
- A new project can be created
- An Excel file can be loaded
- No `FileNotFoundError` or `ModuleNotFoundError` appears

If the app crashes on launch, re-run the build with `console=True` in the spec to see the traceback in a terminal window.

---

### 7. Common issues to handle if they appear

| Symptom | Fix |
|---|---|
| Blank window, no crash | Add `'PySide6.QtSvg'` to `hiddenimports` if SVGs used |
| `FileNotFoundError` on branding.json | Ensure `resource_path()` is used everywhere |
| `ModuleNotFoundError: openpyxl` | Already in hiddenimports; if still failing, add `openpyxl.workbook` |
| App works in dev but crashes frozen | A file path is still using a raw string — grep for remaining `open("` calls |
| Icon not showing | Confirm `assets/icon.ico` exists (user places this manually) |

---

## What NOT to do

- Do not modify any files under `tests/` — they are not part of the distributed app
- Do not modify `docs/` or `.claude/` files
- Do not add `utils/paths.py` to `.gitignore`
- Do not use `--onedir` mode — the client receives a single `.exe`
- Do not hardcode any absolute paths anywhere
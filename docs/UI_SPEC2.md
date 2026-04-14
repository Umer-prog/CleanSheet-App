# CleanSheet — UI Spec v2 (Screen-by-Screen Implementation)

## How to use this file

Work through each section **one at a time**. Do not start the next section until
the current one is visually confirmed against the HTML reference. After each
section, run the app and compare against `design/all_screens.html` at 1280×720.

---

## IMPORTANT — Screen numbering context

The original CleanSheet codebase used a different screen numbering system.
For clarity, here is the mapping between old and new:

| Old label      | New label in this spec  | File to create                  |
|----------------|-------------------------|---------------------------------|
| Screen 0       | Screen 1 — Launcher     | `screens/screen_launcher.py`    |
| (no old equiv) | Screen 2 — Data Loader  | `screens/screen_data_loader.py` |
| (no old equiv) | Screen 3 — Mapper       | `screens/screen_mapper.py`      |
| Screens 6–9    | Screen 4 — Workspace    | `screens/screen_workspace.py`   |

**Popups / dialogs are no longer floating CTk popups.**
They are now proper `QDialog` subclasses — full, modal windows with their own
layouts. Treat each dialog as a proper screen, not a lightweight overlay.
This includes: New Project, Select Sheets, Add to Dimension, Replace Value.

---

## Global rules (apply to every section)

- Fixed window size: `1280 × 720`. Call `setFixedSize(1280, 720)` on QMainWindow.
- All QSS lives in one stylesheet applied to `QApplication` at startup. See `CLAUDE_PYSIDE6_MIGRATION.md`.
- Never use `QTableWidget` — always `QTableView` + `QAbstractTableModel`.
- Never load files on the main thread — always use `FileWorker(QThread)`.
- Emit signals only from screen files — no business logic inside UI files.
- Use `setObjectName()` on every named widget for QSS targeting.
- Reference file for all visuals: `design/all_screens.html` — open at 100% zoom.

---
---

## SECTION 1 — Screen 1: Project Launcher

**File:** `screens/screen_launcher.py`
**Class:** `LauncherScreen(QWidget)`
**Visual reference:** "Screen 1 — Project Launcher" in `design/all_screens.html`

---

### Layout structure

```
QWidget (root, full 1280x720)
└── QHBoxLayout (no margins, no spacing)
    ├── Left panel  QFrame  fixed width 340px
    └── Right panel QFrame  expanding
```

---

### Left panel — QFrame, objectName "launcher_left", fixed width 340px

```
QVBoxLayout (no margins, no spacing)
├── Header row          QFrame, fixed height 64px
│   └── QHBoxLayout
│       ├── QLabel "All Projects"   font 13px, bold, color #f1f5f9
│       └── QLabel count pill       "4 projects", small badge style
├── Search bar          QFrame, fixed height 54px (includes padding)
│   └── QLineEdit       objectName "search_input"
│                       placeholder "Search projects…"
│                       height 34px
├── Project list        QListWidget, objectName "project_list", expanding
│   Each row is a custom delegate showing:
│   - Avatar circle/square (36x36, colored, 2-letter initials)
│   - Project name (13px, #94a3b8, bold when selected #93c5fd)
│   - Client name (11px, #334155)
│   - Left border accent 2px #3b82f6 when selected
└── Footer              QFrame, fixed height 60px
    └── QPushButton "New Project"
        objectName "btn_primary", full width, height 36px
        icon: plus SVG
```

**Signals to emit:**
```python
new_project_requested = Signal()
```

**Behaviour:**
- Typing in search filters `project_list` in real time (filter on project name, case-insensitive)
- Clicking a project row updates the right panel detail section
- "New Project" emits `new_project_requested`

---

### Right panel — QFrame, objectName "launcher_right", expanding

```
QVBoxLayout (no margins, no spacing)
├── Brand hero      QFrame, objectName "brand_hero", fixed height 200px
│   background #13161e
│   QHBoxLayout with left padding 48px, gap 28px
│   ├── Logo QLabel  64x64, blue rounded rect (#3b82f6, radius 16px)
│   │                contains clipboard SVG icon in white
│   └── Text block   QVBoxLayout
│       ├── QLabel "CleanSheet"   font 32px, bold, #f1f5f9, letter-spacing -0.5px
│       └── QLabel "Data Mapping & Standardisation Tool"  font 14px, #475569
│
├── Detail area     QFrame, objectName "detail_area", expanding
│   QVBoxLayout, padding 28px top/left/right
│   ├── Section label   QLabel "Selected Project"
│   │                   10px, uppercase, #334155, letter-spacing
│   ├── Detail card     QFrame, objectName "detail_card"
│   │   background rgba(255,255,255,0.02), border, radius 10px
│   │   QGridLayout, 4 rows:
│   │   Col 0 (fixed 130px): key label, 12px, #475569
│   │   Col 1 (expanding):   value label, 12px, #94a3b8, bold
│   │   Rows:
│   │   - "Project Name"  / project name value
│   │   - "Company"       / company value
│   │   - "Last Modified" / date value
│   │   - "Folder Path"   / path value (11px, monospace, #64748b, elide right)
│   └── Action buttons  QHBoxLayout
│       ├── QPushButton "Open Project"  objectName "btn_primary", expanding, height 38px
│       └── QPushButton "Delete"        objectName "btn_danger", fixed width, height 38px
│
└── Status bar      QFrame, objectName "status_bar", fixed height 36px
    background #13161e, border-top rgba(255,255,255,0.06)
    QHBoxLayout, padding 0 28px
    ├── QLabel "CleanSheet v1.0 · N projects loaded"   11px, #1e293b
    └── Dark mode row: QLabel "Dark Mode" + QCheckBox styled as toggle
```

**Signals to emit:**
```python
open_project_requested  = Signal(str)   # project name
delete_project_requested = Signal(str)  # project name
```

**Behaviour:**
- Selecting a project row populates all 4 detail card rows
- "Open Project" emits `open_project_requested(selected_project_name)`
- "Delete" emits `delete_project_requested(selected_project_name)`
- "Open Project" and "Delete" are disabled (greyed) when no project is selected
- Status bar project count updates dynamically from project list length

---

### Public methods

```python
def load_projects(self, projects: list[dict]) -> None:
    """projects = [{"name": str, "company": str, "modified": str, "path": str}]"""

def set_status(self, count: int) -> None:
    """Updates 'N projects loaded' label in status bar"""
```

---
---

## SECTION 2 — Dialog: New Project

**File:** `dialogs/dialog_new_project.py`
**Class:** `NewProjectDialog(QDialog)`
**Visual reference:** "Screen 2 — New Project Dialog" in `design/all_screens.html`
**Note:** This is a QDialog, not a popup. It is modal and blocks the launcher.

---

### Layout structure

```
QDialog, fixed size 480 x 320, modal
└── QVBoxLayout (no margins)
    ├── Header row      QFrame, fixed height 70px
    │   QHBoxLayout, padding 18px 22px
    │   ├── Icon QLabel  34x34 blue rounded, plus icon
    │   ├── Text block   QVBoxLayout
    │   │   ├── QLabel "New Project"   14px bold #f1f5f9
    │   │   └── QLabel "Fill in the details to create a new workspace"  11px #475569
    │   └── Close btn    QPushButton "✕"  26x26, objectName "btn_close"
    ├── Body            QFrame, padding 24px 22px
    │   QVBoxLayout, gap 16px
    │   ├── Field: "Project Name"
    │   │   QLabel (10px, uppercase, #475569) + QLineEdit (height 38px)
    │   ├── Field: "Company Name"
    │   │   QLabel + QLineEdit
    │   └── Field: "Save Location"
    │       QLabel + QHBoxLayout
    │           ├── QLineEdit  placeholder "Choose a folder…", read-only display
    │           └── QPushButton "Browse…"  objectName "btn_primary", fixed width
    └── Footer row      QFrame, fixed height 56px
        QHBoxLayout, right-aligned
        ├── QPushButton "Cancel"         objectName "btn_ghost"
        └── QPushButton "Create Project" objectName "btn_primary"
```

**Signals to emit:**
```python
project_created = Signal(str, str, str)  # name, company, path
```

**Behaviour:**
- "Browse…" opens `QFileDialog.getExistingDirectory()`
- "Create Project" disabled until all 3 fields are filled
- "Create Project" emits `project_created` then calls `self.accept()`
- "Cancel" and "✕" call `self.reject()`

---
---

## SECTION 3 — Screen 2: Data Loader

**File:** `screens/screen_data_loader.py`
**Class:** `DataLoaderScreen(QWidget)`
**Visual reference:** "Screen 3 — Data Loader" in `design/all_screens.html`

---

### Layout structure

```
QWidget (full 1280x720)
└── QHBoxLayout (no margins)
    ├── Sidebar     QFrame, fixed width 260px, objectName "sidebar"
    └── Main area   QFrame, expanding
```

---

### Sidebar — 260px

```
QVBoxLayout (no margins)
├── Brand block         QFrame, fixed height 64px
│   logo (34x34) + "CleanSheet" (15px bold) + "Data Mapping" (10px muted)
├── Progress steps      QFrame, padding 14px 12px
│   3 step rows, each: step number circle + step label
│   Step states: inactive / active (blue) / done (green checkmark)
│   Steps: 1 Load Files · 2 Select Sheets · 3 Map Columns
│   Current: Step 1 active
├── Project info card   QFrame, margin 8px 12px
│   background rgba(59,130,246,0.06), border rgba(59,130,246,0.12), radius 8px
│   QLabel project name (11px bold #93c5fd) + QLabel company (10px #334155)
└── Footer              QPushButton "← Back to Projects"
                        objectName "btn_ghost", margin 12px
```

---

### Main area

```
QVBoxLayout (no margins)
├── Topbar          QFrame, fixed height 64px, objectName "topbar"
│   Left: QLabel "Data Loader" (15px bold) + QLabel subtitle (11px #334155)
│   Right: QPushButton "+ Add File"  objectName "btn_primary", has plus icon
│
├── Content area    QFrame, expanding, padding 24px 28px
│   QVBoxLayout, gap 16px
│   ├── Info banner     QFrame
│   │   background rgba(59,130,246,0.06), border, radius 8px, padding 10px 14px
│   │   QLabel with info icon + instruction text (12px #60a5fa)
│   └── Files area      QFrame, expanding, objectName "files_area"
│       background rgba(255,255,255,0.02), border, radius 10px
│       QVBoxLayout
│       ├── Files header    QFrame, fixed height 44px
│       │   QLabel "Loaded Files" (uppercase) + QLabel file count
│       └── Content: switches between two states
│           EMPTY STATE:
│               Centered QVBoxLayout
│               Upload icon (52x52, dashed blue border, radius 12px)
│               QLabel "No files added yet"       14px, #64748b
│               QLabel "Click Add File or drag…"  12px, #334155
│           POPULATED STATE:
│               QScrollArea containing file rows
│               Each file row: file icon + filename + sheet badges + remove btn
│
└── Footer bar      QFrame, fixed height 56px, objectName "status_bar"
    Left: QLabel instruction hint (11px #334155)
    Right: QPushButton "Confirm & Continue →"
           objectName "btn_ghost" when disabled
           objectName "btn_primary" when enabled
           Disabled until both Transaction + Dimension sheets are assigned
```

**Signals to emit:**
```python
back_requested         = Signal()
add_file_requested     = Signal()
confirm_requested      = Signal()   # emits only when valid
```

**Behaviour:**
- "Add File" opens `QFileDialog.getOpenFileName()` filtered to `.xlsx .xls .csv`
- Each added file triggers `SelectSheetsDialog` to open immediately
- Confirm button enables only when at least 1 Transaction + 1 Dimension sheet assigned
- File rows show assigned sheet tags (colour-coded T=blue, D=green)

---

### Public methods

```python
def set_project(self, name: str, company: str) -> None
def add_file_row(self, filename: str, sheets: list[dict]) -> None
def set_step_active(self, step: int) -> None   # 1, 2, or 3
def set_confirm_enabled(self, enabled: bool) -> None
```

---
---

## SECTION 4 — Dialog: Select Sheets

**File:** `dialogs/dialog_select_sheets.py`
**Class:** `SelectSheetsDialog(QDialog)`
**Visual reference:** "Screen 4 — Select Sheets Dialog" in `design/all_screens.html`
**Note:** QDialog, modal, opens immediately after a file is added in Data Loader.

---

### Layout structure

```
QDialog, fixed size 520 x auto (max 560), modal
└── QVBoxLayout (no margins)
    ├── Header      QFrame, fixed height 70px
    │   Icon (grid icon, blue) + "Select Sheets" title + filename subtitle (blue mono)
    │   + close button
    ├── Body        QFrame, padding 20px 24px
    │   QLabel "Choose sheets and assign category"  (10px uppercase)
    │   Then for each sheet in file — a sheet row QFrame:
    │   QHBoxLayout:
    │   ├── Checkbox    QCheckBox, custom styled (18x18 blue when checked)
    │   ├── Sheet name  QLabel, 13px, monospace, #cbd5e1
    │   └── Category toggles   QHBoxLayout
    │       ├── QPushButton "Transaction"  toggleable, blue when selected
    │       └── QPushButton "Dimension"   toggleable, green when selected
    │   Unchecked rows are dimmed (opacity effect via setEnabled(False))
    └── Footer      QFrame, fixed height 56px
        QPushButton "Cancel" (ghost) + QPushButton "Confirm Selection" (primary)
```

**Signals to emit:**
```python
sheets_confirmed = Signal(list)
# list of {"name": str, "category": "Transaction"|"Dimension"} for checked sheets only
```

**Behaviour:**
- Unchecking a sheet disables its category toggle buttons
- A sheet cannot be confirmed without a category assigned if checked
- "Confirm Selection" disabled until all checked sheets have a category
- Checking a sheet auto-focuses its Transaction button as default

---
---

## SECTION 5 — Screen 3: Mapper

**File:** `screens/screen_mapper.py`
**Class:** `MapperScreen(QWidget)`
**Visual reference:** "Screen 5 — Mapper" in `design/all_screens.html`

---

### Layout structure

```
QWidget (full 1280x720)
└── QHBoxLayout (no margins)
    ├── Sidebar     QFrame, fixed width 260px
    └── Main area   QFrame, expanding
```

---

### Sidebar — same brand block as Data Loader

```
Steps: Step 1 done · Step 2 done · Step 3 active
Project info card
Footer: QPushButton "← Back to Data Loader"
```

---

### Main area

```
QVBoxLayout (no margins)
├── Topbar          QFrame, fixed height 64px
│   QLabel "Mapper" + subtitle instruction text
│
├── Content         QFrame, expanding, padding 20px 28px
│   QVBoxLayout, gap 16px
│   ├── Table picker row    QHBoxLayout, gap 16px
│   │   ├── Dimension panel     QFrame (half width)
│   │   │   Header: "Dimension Tables" label + count badge (green)
│   │   │   Body: list of QPushButton per dimension table
│   │   │   Selected state: green tint bg + green border
│   │   └── Transaction panel   QFrame (half width)
│   │       Header: "Transaction Tables" label + count badge (blue)
│   │       Body: list of QPushButton per transaction table
│   │       Selected state: blue tint bg + blue border
│   │
│   ├── Column picker row   3-column QHBoxLayout
│   │   ├── Dimension column panel  QFrame
│   │   │   Label "Dimension Column" + QComboBox (blue style)
│   │   ├── Centre: QPushButton "Confirm Mapping"  objectName "btn_primary"
│   │   └── Transaction column panel QFrame
│   │       Label "Transaction Column" + QComboBox (blue style)
│   │
│   └── Confirmed mappings  QFrame, objectName "mappings_panel"
│       Header: "Confirmed Mappings" + count badge
│       Scrollable list of mapping rows:
│       Each row: mapping text (mono) + remove QPushButton (danger, 26x26)
│
└── Footer bar      QFrame, fixed height 56px
    Left: hint label
    Right: QPushButton "Finish Setup →"  objectName "btn_primary"
```

**Signals to emit:**
```python
back_requested        = Signal()
mapping_confirmed     = Signal(str, str, str, str)  # dim_table, dim_col, txn_table, txn_col
mapping_removed       = Signal(int)                  # index of mapping to remove
finish_requested      = Signal()
```

**Behaviour:**
- Selecting a dimension table populates the Dimension Column QComboBox
- Selecting a transaction table populates the Transaction Column QComboBox
- "Confirm Mapping" adds a row to the mappings list and resets both selectors
- "Confirm Mapping" disabled unless both a table and column are selected on each side
- "Finish Setup" disabled until every loaded table appears in at least one mapping
- Remove button on a mapping row emits `mapping_removed(index)`

---

### Public methods

```python
def load_tables(self, dimension: list[str], transaction: list[str]) -> None
def load_columns(self, side: str, columns: list[str]) -> None  # side = "dimension"|"transaction"
def add_mapping_row(self, dim_table: str, dim_col: str, txn_table: str, txn_col: str) -> None
def remove_mapping_row(self, index: int) -> None
def set_finish_enabled(self, enabled: bool) -> None
```

---
---

## SECTION 6 — Screen 4: Workspace (no errors state)

**File:** `screens/screen_workspace.py`
**Class:** `WorkspaceScreen(QWidget)`
**Visual reference:** "Screen 6A — Workspace (No Errors)" in `design/all_screens.html`
**Note:** This is the main daily-use screen. It has two visual states: no-errors and
with-errors. Build both states in the same file, toggled by data.

---

### Layout structure

```
QWidget (full 1280x720)
└── QHBoxLayout (no margins)
    ├── Sidebar     QFrame, fixed width 260px
    └── Main area   QFrame, expanding
```

---

### Sidebar

```
QVBoxLayout (no margins)
├── Brand block         QFrame, fixed height 64px
├── Workspace info      QFrame, padding 12px, border-bottom
│   QLabel "WORKSPACE" (10px muted uppercase)
│   QLabel project name (13px bold #f1f5f9)
│   QLabel company (11px #475569)
├── Back button         QPushButton "← Back to Launcher"
│                       objectName "btn_ghost", margin 8px 12px
├── Section label       QLabel "MAPPINGS"
├── Mapping nav items   One QFrame per mapping, objectName "nav_mapping"
│   Each shows: mapping name (11px mono) + status badge on right
│   Badge: green "✓" when clean, red count "N" when errors exist
│   Selected state: blue left border + blue tint
├── Divider             QFrame, 1px horizontal line
└── Bottom nav items    4 x QFrame nav rows (icon + label):
    T Sources / D Sources / History / Settings
    objectName "nav_item", active state = blue left border
```

---

### Main area — Topbar

```
QFrame, fixed height 64px, objectName "topbar", background #13161e
QHBoxLayout, padding 0 24px
Left:
  Mapping title row: QLabel from_col + QLabel "→" + QLabel to_col (blue)
  Error badge: QLabel "N errors" — red pill, visible only when errors > 0
Right:
  Pagination: QLabel "Rows X–Y of Z" + QPushButton "Prev" + QPushButton "Next"
  QPushButton "↻ Refresh"  objectName "btn_ghost"
```

---

### Main area — Content split (expanding)

```
QVBoxLayout (no margins)
├── Table section   QFrame, fixed height 300px
│   ├── Section header  QFrame, fixed height 38px
│   │   QLabel "Transaction Data Preview" + hint label (right)
│   └── QTableView, objectName "main_table", expanding
│       Model: PandasModel wrapping the transaction DataFrame
│       Error rows: custom delegate paints red left stripe + red cell for bad value
│       Clicking a row selects the corresponding error in the errors panel
│
└── Errors section  QFrame, expanding
    TWO STATES:
    NO ERRORS STATE:
        Centered QVBoxLayout
        Green icon (40x40, checkmark)
        QLabel "No errors found"        13px, #34d399
        QLabel "All values match…"      12px, #334155
    WITH ERRORS STATE:
        ├── Errors header   QFrame, fixed height 44px
        │   QLabel "ERRORS" (red, with warning icon) + count badge (red)
        └── Errors list     QScrollArea
            Each error row is a QFrame (clickable):
            Row num badge (mono) + column name + "·" + bad value (red mono) + tag pill
            Selected state: red tint bg + red border
```

---

### Main area — Footer bar

```
QFrame, fixed height 56px, objectName "status_bar", background #13161e
QHBoxLayout, padding 0 20px
Left:
  NO ERRORS: QLabel "All errors resolved — ready to generate output"
  WITH ERRORS: QLabel "N error selected — choose an action to resolve it"
               (N is highlighted red)
Right:
  NO ERRORS:   QPushButton "Generate Output →"  objectName "btn_primary" (green #059669)
  WITH ERRORS: QPushButton "Generate Output"     objectName "btn_ghost" (disabled look)
               QPushButton "Replace Value"        objectName "btn_replace" (blue ghost)
               QPushButton "Add to Dimension"     objectName "btn_primary" (blue)
```

**Signals to emit:**
```python
mapping_selected         = Signal(str)        # mapping key clicked in sidebar
nav_item_selected        = Signal(str)        # "t_sources"|"d_sources"|"history"|"settings"
back_requested           = Signal()
refresh_requested        = Signal()
error_selected           = Signal(int)        # row index of selected error
replace_requested        = Signal(int)        # row index to replace
add_dimension_requested  = Signal(int)        # row index to add
generate_requested       = Signal()
page_prev_requested      = Signal()
page_next_requested      = Signal()
```

---

### Public methods

```python
def load_mapping(self, from_col: str, to_col: str, df: pd.DataFrame) -> None
def set_errors(self, errors: list[dict]) -> None
    # errors = [{"row": int, "column": str, "value": str}]
def set_mappings_nav(self, mappings: list[dict]) -> None
    # mappings = [{"label": str, "error_count": int, "active": bool}]
def set_pagination(self, current_start: int, current_end: int, total: int) -> None
def set_workspace_info(self, name: str, company: str) -> None
def highlight_error_row(self, row_index: int) -> None
```

---
---

## SECTION 7 — Dialog: Replace Value

**File:** `dialogs/dialog_replace.py`
**Class:** `ReplaceDialog(QDialog)`
**Visual reference:** "Screen 6D — Replace Value Dialog" in `design/all_screens.html`
**Note:** QDialog, modal, opens from workspace footer "Replace Value" button.

---

### Layout structure

```
QDialog, fixed size 520 x 420, modal
└── QVBoxLayout (no margins)
    ├── Header          QFrame, 70px — blue edit icon + title + subtitle (table name in mono blue)
    ├── Body            QFrame, padding 20px 22px
    │   QVBoxLayout, gap 12px
    │   ├── Current value strip     QFrame
    │   │   background rgba(239,68,68,0.06), border red-tinted, radius 8px
    │   │   warning icon + "Current bad value:" label + value (red mono) + hint
    │   ├── Dimension table         QFrame, objectName "dim_table_frame"
    │   │   background rgba(255,255,255,0.02), border, radius 9px
    │   │   ├── Table header    QFrame, 36px
    │   │   │   QLabel "Dimension Table" + QLabel table name (mono blue) + row count
    │   │   ├── Column header   QFrame — one QLabel per column (10px uppercase)
    │   │   └── QListWidget     objectName "dim_row_list", max height 180px
    │   │       Each item: custom delegate showing all column values in a row
    │   │       Selected row: blue tint
    │   └── Replacement preview     QFrame
    │       background rgba(59,130,246,0.06), border blue-tinted, radius 8px
    │       checkmark icon + "Will replace:" + bad_value (red mono) + "→" + new_value (green mono)
    └── Footer          QFrame, 56px
        Left: hint label
        QPushButton "Cancel" (ghost) + QPushButton "Apply Replace" (primary)
```

**Signals to emit:**
```python
replace_confirmed = Signal(str, str)  # bad_value, replacement_value
```

**Behaviour:**
- Constructor receives `bad_value: str`, `dimension_df: pd.DataFrame`
- Dimension rows rendered from DataFrame — all columns shown
- Selecting a row updates the replacement preview live
- "Apply Replace" disabled until a row is selected
- "Apply Replace" emits `replace_confirmed` then `self.accept()`

---
---

## SECTION 8 — Dialog: Add to Dimension

**File:** `dialogs/dialog_add_dimension.py`
**Class:** `AddDimensionDialog(QDialog)`
**Visual reference:** "Screen 6C — Add to Dimension Dialog" in `design/all_screens.html`
**Note:** QDialog, modal, opens from workspace footer "Add to Dimension" button.
This dialog must scale to any number of columns — do not hardcode fields.

---

### Layout structure

```
QDialog, fixed size 620 x 580, modal
└── QVBoxLayout (no margins)
    ├── Header          QFrame, 70px — green plus icon + title + table name subtitle
    ├── Error strip     QFrame, fixed height 38px
    │   background rgba(239,68,68,0.05), border-bottom red-tinted
    │   warning icon + "Error value:" label + bad_value (red mono) + hint text
    ├── Scrollable body QScrollArea, expanding
    │   QWidget > QVBoxLayout, padding 16px 22px
    │   Fields rendered dynamically from column schema:
    │   Layout: QGridLayout, 2 columns
    │   ┌─ Section divider: "Key Column" (full width)
    │   │  Key column field (full width, grid-column span 2):
    │   │  label with "Pre-filled · Key" badge + read-only QLineEdit (red style, value = bad_value)
    │   ├─ Section divider: "Required Columns" (full width)
    │   │  One field per required column (NOT the key), in 2-col grid:
    │   │  label with "Required" badge (red) + QLineEdit
    │   └─ Section divider: "Optional Columns" (full width)
    │      One field per optional column, in 2-col grid:
    │      label with "Optional" badge (grey) + QLineEdit
    └── Footer          QFrame, 56px
        Left: QLabel "N required fields must be filled"  (N in red)
        QPushButton "Cancel" (ghost) + QPushButton "Add Row to Dimension" (green #059669)
```

**Signals to emit:**
```python
row_added = Signal(dict)  # {column_name: value} for all columns
```

**Constructor signature:**
```python
def __init__(
    self,
    bad_value: str,
    table_name: str,
    key_column: str,
    required_columns: list[str],
    optional_columns: list[str],
    parent=None
)
```

**Behaviour:**
- Fields are generated dynamically from `required_columns` and `optional_columns` lists
- Key column field is pre-filled with `bad_value` and is read-only
- "Add Row to Dimension" disabled until all required fields are non-empty
- Footer hint updates live: counts unfilled required fields
- On confirm: collects all field values into a dict and emits `row_added`

---
---

## SECTION 9 — Screen: Transaction Sources

**File:** `screens/screen_sources.py`
**Class:** `SourcesScreen(QWidget)`
**Visual reference:** "Screen 7 — Transaction Sources" in `design/all_screens.html`
**Note:** Handles both T Sources and D Sources — pass a mode flag to the constructor.

---

### Layout

```
QWidget (full 1280x720)
└── QHBoxLayout
    ├── Sidebar (same as workspace, T Sources nav item active)
    └── Main area
        ├── Topbar      title changes: "Transaction Sources" or "Dimension Sources"
        │               Right: QPushButton "+ Add Transaction Table" or "+ Add Dimension Table"
        ├── Content     padding 24px 28px
        │   QFrame card (section_card style):
        │   Header: "Current Transaction Tables" or "Current Dimension Tables" + count
        │   Rows: one per table
        │   Each row: file icon + table name + meta text + Upload New Version btn + Delete btn
        └── (no footer bar needed)
```

**Signals to emit:**
```python
add_requested           = Signal()
upload_version_requested = Signal(str)   # table name
delete_requested        = Signal(str)    # table name
nav_item_selected       = Signal(str)
back_requested          = Signal()
```

---
---

## SECTION 10 — Screen: History / Revert

**File:** `screens/screen_history.py`
**Class:** `HistoryScreen(QWidget)`
**Visual reference:** "Screen 8 — History / Revert" in `design/all_screens.html`

---

### Layout

```
QWidget (full 1280x720)
└── QHBoxLayout
    ├── Sidebar (History nav item active)
    └── Main area
        ├── Topbar      "History / Revert" + Refresh button (right)
        └── Content split (expanding, horizontal)
            ├── Left panel  QFrame, fixed width 340px, border-right
            │   Header: "Snapshots" label + count
            │   QListWidget of snapshot rows:
            │   Each: snapshot name (12px bold) + date (11px muted)
            │   Selected: blue tint
            └── Right panel QFrame, expanding
                EMPTY STATE (no snapshot selected):
                    Centered icon + "Select a snapshot to view details" text
                POPULATED STATE:
                    Detail rows (key/value pairs from manifest)
                Footer (always visible):
                    QLineEdit placeholder "Label this snapshot…"
                    QPushButton "Save Label"  objectName "btn_ghost"
                    QPushButton "Revert to This Version"  objectName "btn_revert"
```

**Signals to emit:**
```python
refresh_requested       = Signal()
snapshot_selected       = Signal(str)   # snapshot id
save_label_requested    = Signal(str, str)  # snapshot id, label text
revert_requested        = Signal(str)   # snapshot id
nav_item_selected       = Signal(str)
back_requested          = Signal()
```

---
---

## SECTION 11 — Screen: Settings

**File:** `screens/screen_settings.py`
**Class:** `SettingsScreen(QWidget)`
**Visual reference:** "Screen 9 — Settings" in `design/all_screens.html`

---

### Layout

```
QWidget (full 1280x720)
└── QHBoxLayout
    ├── Sidebar (Settings nav item active)
    └── Main area
        ├── Topbar      "Settings" + subtitle "Update project details and preferences"
        ├── Content     padding 28px, QVBoxLayout
        │   max-width container 520px (use QWidget with fixed max width)
        │   Fields:
        │   ├── "Project Name"   QLabel (uppercase) + QLineEdit (editable)
        │   ├── "Company Name"   QLabel + QLineEdit (editable)
        │   ├── "Project Folder Path (read-only)"
        │   │   QLabel + QLineEdit (read-only, muted style, monospace)
        │   └── "History Enabled"
        │       QHBoxLayout: QCheckBox (styled toggle) + QLabel "History Enabled"
        └── Footer bar  QFrame, fixed height 52px, objectName "status_bar"
            Right: QPushButton "Save Changes"  objectName "btn_primary"
```

**Signals to emit:**
```python
save_requested    = Signal(str, str, bool)  # name, company, history_enabled
nav_item_selected = Signal(str)
back_requested    = Signal()
```

**Public methods:**
```python
def load_settings(self, name: str, company: str, path: str, history_enabled: bool) -> None
```

---
---

## File structure summary

When all sections are complete, the project should have:

```
project_root/
├── main.py
├── main_window.py
├── CLAUDE_PYSIDE6_MIGRATION.md
├── UI_SPEC_V2.md  (this file)
├── design/
│   └── all_screens.html
├── screens/
│   ├── screen_launcher.py
│   ├── screen_data_loader.py
│   ├── screen_mapper.py
│   ├── screen_workspace.py
│   ├── screen_sources.py
│   ├── screen_history.py
│   └── screen_settings.py
├── dialogs/
│   ├── dialog_new_project.py
│   ├── dialog_select_sheets.py
│   ├── dialog_replace.py
│   └── dialog_add_dimension.py
└── workers/
    └── file_worker.py
```

---

## How to use this file with Claude Code

Start each session with:

```
Read UI_SPEC_V2.md and CLAUDE_PYSIDE6_MIGRATION.md before writing any code.
We are working on SECTION N today.
Visual reference is in design/all_screens.html — open it and match exactly.
Build only what is listed under Section N. Do not touch other files.
```

Work one section per session. Confirm visually before moving on.
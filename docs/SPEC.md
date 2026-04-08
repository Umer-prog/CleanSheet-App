# [APPNAME] — Full Project Specification
# NOTE: App name TBD — replace [APPNAME] everywhere once decided

## Overview
[APPNAME] is a desktop data standardization app built in Python using CustomTkinter.
Its core purpose: load data from Excel files (and later DBs), apply column-level mappings
to fix inconsistencies (spelling errors, whitespace, wrong values), and return corrected
output files. Each client interaction is organized as a self-contained "project/module."

---

## Tech Stack
- Language: Python 3.11+
- UI: CustomTkinter
- Excel reading: pandas + openpyxl
- Fuzzy matching: rapidfuzz
- Internal storage: JSON (dim tables, mappings), CSV (transaction tables)
- Snapshot/history: file-based with hashing (hashlib md5)
- Packaging: PyInstaller (.exe for clients)

---

## Core Concepts

### Project / Module
Every client dataset is a "project." A project is a folder on disk containing all data,
mappings, history, and config for that dataset. Projects are independent — changing one
does not affect another. Structural changes (new columns, renamed columns) require a
new project.

### Transaction Tables
- Uploaded as Excel sheets, saved internally as CSV (one file per sheet)
- Updated frequently by clients (new data comes in regularly)
- Full history tracked via snapshot/manifest system
- Can be deleted from a project
- Errors are detected by comparing their mapped columns against dim table values

### Dimension Tables
- Uploaded as Excel sheets, saved internally as JSON (one file per sheet)
- Permanent reference/lookup tables (salesperson list, item list, region list, etc.)
- Cannot be replaced or deleted once added
- New dim tables can be added at any time
- If a dim table with the same name already exists → show error, block addition
- New rows can be appended to existing dim tables (via the Add flow in Screen 3)

### Mappings
- A mapping is a relationship: Transaction Table [column] ↔ Dim Table [column]
- One transaction table can have multiple mappings (one per dim table it links to)
- Each mapping is created one at a time (select t-table, select d-table, select columns, confirm)
- Every added sheet must be part of at least one mapping — enforced at confirm time
- Mappings are stored in JSON in the mapping store folder
- Mappings are never affected when dim table data is appended or transaction tables updated

### Error Detection
- For each mapping: compare every value in the transaction column against all values in the linked dim column
- All comparisons are full string comparisons (handles whitespace, wrong spelling, null/blank, wrong values)
- An error = a value in the transaction column that has no exact match in the dim column
- Errors are shown per mapping (clicking a mapping in the navbar shows its errors)

---

## Folder Structure (per project)

```
<project_root>/                        ← chosen by client in settings
  <ProjectName>/
    project.json                       ← project metadata (name, created date, settings)
    |
    data/                              ← current active data (what the app reads day-to-day)
    |   transactions/
    |   |   posted_fact_table.csv
    |   |   order_fact_table.csv
    |   dim/
    |       item_dim.json
    |       customer_dim.json
    |       region_dim.json
    |
    history/                           ← snapshot archive (transaction tables only)
    |   manifest_001/
    |   |   manifest.json              ← {id, date, label, tables: {name: filename}}
    |   |   posted_fact_table_a1b2.csv ← content-addressed copy
    |   |   order_fact_table_c3d4.csv
    |   manifest_002/
    |       manifest.json
    |       posted_fact_table_e5f6.csv ← only new/changed files copied here
    |
    mappings/
    |   mapping_store.json             ← list of all mapping relationships
    |
    settings.json                      ← history on/off, project path, other prefs
```

### mapping_store.json structure
```json
{
  "mappings": [
    {
      "id": "map_001",
      "transaction_table": "posted_fact_table",
      "transaction_column": "item_col",
      "dim_table": "item_dim",
      "dim_column": "item_name"
    },
    {
      "id": "map_002",
      "transaction_table": "posted_fact_table",
      "transaction_column": "customer_col",
      "dim_table": "customer_dim",
      "dim_column": "customer_name"
    }
  ]
}
```

### manifest.json structure
```json
{
  "manifest_id": "manifest_003",
  "created_at": "2025-04-01 10:32",
  "label": "April payroll update",
  "tables": {
    "posted_fact_table": "posted_fact_table_e5f6.csv",
    "order_fact_table":  "order_fact_table_c3d4.csv"
  }
}
```

### project.json structure
```json
{
  "project_name": "Sales Module",
  "created_at": "2025-01-15",
  "company": "Acme Corp",
  "transaction_tables": ["posted_fact_table", "order_fact_table"],
  "dim_tables": ["item_dim", "customer_dim"]
}
```

---

## Snapshot / History System

### How it works
1. Every time a transaction table is uploaded/updated, its content is hashed (MD5, first 8 chars)
2. The hashed CSV is saved inside the new manifest folder: `tablename_hash.csv`
3. If the hash already exists in that manifest folder, the file is not re-copied (deduplication)
4. A new `manifest.json` is created pointing each table to its file
5. The `data/transactions/` folder is updated with the latest version (always reflects current)
6. `settings.json` tracks which manifest is "current"

### History on/off (from settings)
- History ON (default): every upload creates a new manifest folder with full tracking
- History OFF: no manifest folders created, no history kept, only `data/` is updated
- Setting can be changed per project in settings screen

### Reverting
- User opens the history/revert screen
- Sees a list of all manifests with their human-readable labels and dates
- Selects one and confirms
- App copies the files from that manifest folder back into `data/transactions/`
- Updates `settings.json` to mark that manifest as current
- Does NOT delete newer manifests — revert is just a restore, history stays intact

### Hashing logic
```python
import hashlib

def hash_dataframe(df):
    content = df.to_csv(index=False).encode()
    return hashlib.md5(content).hexdigest()[:8]

# filename: posted_fact_table_a1b2c3d4.csv
```

---

## Window & Layout

- Fixed window size: **1280×720** (not resizable, not full screen)
- All screens must be designed to fit within 1280×720 without scrolling at the top level
- Panels, tables, and lists may scroll internally

---

## Screen-by-Screen Specification

---

### Screen 0 — Project Launcher
**Trigger:** App opens  
**Layout:** VSCode-style new window

**Left panel:** List of existing projects (name, company, last modified date)  
**Right panel:** Two options — "New Project" button, "Open Selected" button

**Clicking an existing project:** highlights it, Open button activates  
**New Project:** opens a dialog asking for Project Name, Company Name, and folder path (browse button)  
→ Creates the folder structure on disk  
→ Navigates to Screen 1 (Stage 1 setup)

**Opening existing project:** navigates to Screen 3 (Stage 2 working screen)

---

### Screen 1 — Add Data Sources (Stage 1 only)
**Trigger:** New project created  
**Purpose:** Client adds Excel files and selects/categorizes their sheets

**Layout:**
- Top: "Add File" button
- Middle: List of added files, each showing its selected sheets and their category (Transaction/Dimension)
- Bottom: "Confirm & Continue" button → goes to Screen 2

**Add File flow:**
1. File browser opens → client selects an Excel file
2. Popup appears (Power BI style) showing all sheets in that file as checkboxes
3. Client checks the sheets they want
4. Each checked sheet gets a dropdown: Transaction | Dimension
5. Client clicks OK → returns to Screen 1 with the file and sheets listed
6. Client can add more files (repeat) or delete a file/sheet from the list

**Validation on Confirm:**
- At least one transaction sheet must be selected
- At least one dimension sheet must be selected
- All sheets must have a category selected
- If validation fails → show error message, block navigation

---

### Screen 2 — Define Mappings (Stage 1 only)
**Trigger:** Confirmed from Screen 1  
**Purpose:** Client defines which transaction column links to which dim column

**Layout:**
- Top-left table: all added Dimension sheets
- Top-right table: all added Transaction sheets  
- Below: two dropdowns — one for dim column, one for transaction column
- Confirm button adds the mapping to the list below
- Bottom: list of all confirmed mappings, each with X to delete
- Final: "Finish Setup" button

**Mapping flow (one at a time):**
1. Client clicks a dim sheet from the left table → highlights it
2. Client clicks a transaction sheet from the right table → highlights it
3. Two dropdowns appear: "Column from [dim sheet]" and "Column from [transaction sheet]"
4. Client selects columns from each dropdown
5. Clicks Confirm → mapping added to list, selections cleared
6. Repeat for all needed mappings

**Validation on Finish Setup:**
- Every added sheet (both transaction and dim) must appear in at least one mapping
- If any sheet is unmapped → show which ones are missing, block navigation
- On success → project setup complete, navigate to Screen 3

---

### Screen 3 — Main Working Screen (Stage 2)
**Trigger:** Existing project opened  
**Layout:** Left navbar + main content area (frame switching, no full re-render)

**Left Navbar items:**
- One entry per defined mapping (e.g. "posted → item_dim", "posted → customer_dim")
- Separator
- "T Sources" (transaction table management)
- "D Sources" (dimension table management)
- Separator  
- "History / Revert"
- "Settings"

**Default view (mapping selected):**
- Top area: transaction table data displayed as a grid/table
- Bottom area: error list for this mapping
  - Each error row shows: row number, column name, bad value, expected values (from dim)
  - Click an error → shows two buttons: Replace | Add

**Replace flow:**
1. Popup opens showing all valid values from the linked dim column
2. Client selects the correct value
3. Confirms → that cell in the transaction CSV is updated
4. Error removed from list

**Add flow:**
1. Popup opens showing all columns of the dim table (except the mapped column which is pre-filled with the bad value)
2. All fields are required
3. Client fills in remaining fields and confirms
4. New row appended to the dim JSON file
5. Error removed from list (value now exists in dim table)

---

### Screen 3 — T Sources view
**Trigger:** Click "T Sources" in navbar  
**Shows:** List of all transaction tables currently in the project

**Actions per table:**
- Upload new version → triggers file browser → select Excel → select sheet → confirm
  - New CSV saved, new manifest created (if history ON)
  - data/transactions/ updated
- Delete table → confirmation popup → removes from project, removes its mappings too
  - Warning shown: "Deleting this table will also remove X mappings. Confirm?"

**Add new transaction table:**
- Same flow as Screen 1 (file browser → sheet popup → category already = Transaction)
- After adding → must go define its mapping (prompt shown: "Go to mapping setup?")

---

### Screen 3 — D Sources view
**Trigger:** Click "D Sources" in navbar  
**Shows:** List of all dimension tables currently in the project

**Actions:**
- Add new dim table → file browser → sheet popup → category = Dimension
  - If same name already exists → error shown, blocked
  - After adding → must define mapping (same prompt as above)
- Cannot delete existing dim tables
- Cannot replace existing dim tables (tooltip shown explaining why)

---

### Screen 3 — History / Revert view
**Trigger:** Click "History / Revert" in navbar  
**Shows:** List of all manifests in chronological order

**Each manifest row shows:**
- Manifest ID
- Date and time
- Human-readable label (editable after creation)
- Which tables are included

**Actions:**
- Click a manifest → see detail of which files it points to
- "Revert to this version" button → confirmation popup → restores that manifest to data/
- Revert does NOT delete newer manifests

**Only visible if history is ON in settings**

---

### Screen 3 — Settings view
**Trigger:** Click "Settings" in navbar

**Options:**
- Project name (editable)
- Company name (editable)  
- Project folder path (read-only, shown for reference)
- History: ON / OFF toggle
  - If turned OFF: warning shown "Existing history will be kept but no new snapshots will be created"
- Save button

---

## Settings File (settings.json)
```json
{
  "history_enabled": true,
  "current_manifest": "manifest_005",
  "project_path": "C:/Users/client/Documents/Workfolio/SalesModule"
}
```

---

## What is NOT in scope (deferred to later)
- DB connections (same logic as Excel, deferred)
- Fuzzy match suggestions (show closest dim value as suggestion in Replace popup — add later)
- Batch processing multiple files at once
- Scheduled/automated runs
- Export/output file generation (separate layer, designed later)
- Multi-user / shared projects

---

## Open Decision (confirm before building)
- Gap 5 confirmed: error detection scope = string comparison of mapped columns only
  (covers whitespace, spelling, nulls, wrong values — all handled as string mismatch)

---

## Confirmed Decisions

### Error detection scope (Gap 5)
- Current scope: full string comparison of mapped columns only
- Covers: whitespace, wrong spelling, null/blank cells, completely wrong values
- All values treated as strings — no type checking needed at this stage
- **Extensibility:** error detector must be built as a pipeline of check functions.
  Each check is a separate function. New checks added by dropping into the pipeline
  without touching existing code.

```python
# Pattern to follow in core/error_detector.py
ERROR_CHECKS = [
    check_against_dim_values,   # current scope
    # check_null_or_blank,      # future
    # check_numeric_format,     # future
]

def run_checks(value, dim_values, **kwargs):
    errors = []
    for check in ERROR_CHECKS:
        result = check(value, dim_values, **kwargs)
        if result:
            errors.append(result)
    return errors
```

---

## Branding & Theming System

### Overview
Each deployed instance can be customized with a company logo and color scheme.
Configured at deployment time via branding.json — NOT changeable inside the app by clients.
Developer edits branding.json, repackages with PyInstaller, delivers branded .exe to client.

### branding.json structure
```json
{
  "company_name": "Acme Corp",
  "logo_path": "assets/logo.png",
  "color_scheme": {
    "primary":      "#1A73E8",
    "secondary":    "#F1F3F4",
    "accent":       "#EA4335",
    "text_dark":    "#202124",
    "text_light":   "#FFFFFF",
    "sidebar_bg":   "#1A73E8",
    "sidebar_text": "#FFFFFF"
  }
}
```

### Color key meanings
- primary: main buttons, navbar highlight, active states
- secondary: background surfaces, card backgrounds
- accent: error highlights, delete buttons, warnings
- sidebar_bg / sidebar_text: left navbar in Screen 3
- Never hardcode colors in UI files — always use theme.get("primary")

### theme.py (ui/theme.py)
Single module loaded at app start. All UI files import from here.
```python
import json
from pathlib import Path

_branding = {}

def load(branding_path: Path):
    global _branding
    if branding_path.exists():
        with open(branding_path) as f:
            _branding = json.load(f)

def get(key: str, fallback: str = "#2B5CE6") -> str:
    return _branding.get("color_scheme", {}).get(key, fallback)

def company_name() -> str:
    return _branding.get("company_name", "DataApp")

def logo_path():
    p = _branding.get("logo_path")
    return Path(p) if p else None
```

### Logo rules
- Format: PNG, transparent background recommended
- Shown in: top-left of main window, Screen 0 launcher
- If file missing: falls back to company_name text only

### Default branding (no branding.json present)
```json
{
  "company_name": "[APPNAME]",
  "logo_path": null,
  "color_scheme": {
    "primary":      "#2B5CE6",
    "secondary":    "#F5F5F5",
    "accent":       "#E63946",
    "text_dark":    "#1A1A2E",
    "text_light":   "#FFFFFF",
    "sidebar_bg":   "#2B5CE6",
    "sidebar_text": "#FFFFFF"
  }
}
```

### Deployment steps per new client
1. Edit branding.json with client colors and company name
2. Drop logo PNG into assets/
3. Repackage with PyInstaller
4. Deliver branded .exe to client

---

## App Name
TBD — replace [APPNAME] everywhere once confirmed.
Candidates: Mapflow, Veriflow, Cleansheet, Mappiq, Datarule

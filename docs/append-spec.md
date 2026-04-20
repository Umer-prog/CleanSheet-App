
## Overview
 
Sheet chaining allows a user to merge multiple sheets (from different files) into a single logical table before mapping or saving. The merged result is a unified CSV with an appended `source` column indicating origin. A metadata flag marks whether a table is "chained" or "normal", for downstream handling in later screens.
 
This feature inserts a new intermediate screen **(Screen 1.5 — Sheet Column Mapper)** between the Data Loader (Screen 1) and the Mapper (Screen 2).
 
---
 
## Section 1 — Data Model & Storage Changes
 
**Goal:** Define what needs to be added to the existing data layer to support chaining. The implementer should fit these additions into the project's existing model and storage patterns — do not restructure what already exists.
 
### 1.1 Sheet Record Changes
 
Each sheet entry in the project manifest needs two new fields added to it. The first is a boolean flag that marks whether this sheet is chained. The second is a list that holds the chain entries in order. For a normal unchained sheet, the flag is false and the list is null or absent. These fields are what downstream screens will read to know how to handle a sheet differently.
 
### 1.2 Chain Entry Structure
 
Each item in the chain list needs to store the following pieces of information: its position in the chain (an integer order starting from zero), the absolute file path of the source xlsx file, the name of the specific sheet within that file, a short display label for the file (the filename is sufficient), and the column mapping for that entry. The column mapping describes how each column in this entry's sheet corresponds to a column in the primary sheet. For the first entry in the chain (order zero, the primary), the column mapping is null because its columns are the reference — they are not remapped. For every subsequent entry, the column mapping is a simple key-value pair where the key is the primary column name and the value is the name of the matching column in that secondary sheet.
 
### 1.3 Primary vs Secondary
 
The first entry in the chain (order zero) is always the primary. It is the sheet that was originally added to the project. Its columns define the schema that all other entries must map to. If the primary is ever removed via its chain link delete, the next entry in order becomes the new primary and its column mapping is cleared since it is now the reference. This promotion logic must be handled in the project manager layer.
 
### 1.4 Unified CSV Output
 
When a sheet is chained, its output is a single merged CSV file rather than individual files per source. The implementer should create a service responsible for producing this file. It reads each chain entry in order, applies the column mapping to rename columns in secondary entries so they align with the primary's column names, discards any columns from secondary entries that were not mapped, and stacks all the rows together. A column named `source` is appended as the last column in the output, with its value set to the file label of whichever entry each row came from. The primary's rows are included with the primary's file label as their source value.
 
If a secondary entry has columns that were not mapped to any primary column, those extra columns are still included in the unified output rather than discarded. For rows that come from sources where those extra columns do not exist — meaning the primary and any other secondary entries that lack them — the value is left empty. This means the final unified CSV can be wider than the primary alone, with some cells being empty depending on which source each row came from.
 
This service must be callable both when a new chain link is confirmed and when a chain link is removed, so the output stays in sync with the current chain state at all times. If a chain collapses back to a single entry, the service should produce a plain CSV without the `source` column, matching the format of a normal non-chained sheet output.
 
---
 
## Section 2 — Loaded Files Panel UI Changes (Screen 1) [REFINED]
 
**Goal:** Add a chain-add button and per-link chain removes to each sheet row, while keeping the existing sheet-level delete and file-level remove completely unchanged.
 
---
 
### 2.0 Three Levels of Remove
 
There are three independent remove actions in this panel and they must never interfere with each other.
 
The **file-level remove** sits at the top right of a file card and removes the entire card along with every sheet inside it. This is existing behaviour and is not touched.
 
The **sheet-level delete** sits at the far right of each sheet row and removes that sheet entry from the project entirely. If the sheet had a chain, the entire chain is discarded along with it. This is existing behaviour and is not touched.
 
The **chain link remove** is new. It is a small delete control that appears inline next to each individual sheet pill inside a chained row. It removes only that one link from the chain, leaving the rest intact.
 
---
 
### 2.1 Layout — Normal (Unchained) Sheet Row
 
Every sheet row, whether chained or not, gets a `[+]` button placed at the far right — just before the existing sheet-level delete. The `[+]` is always visible for all sheet types (T and D). It is how the user initiates a chain. If the user never clicks it, the sheet behaves exactly as before and is treated as a normal non-chained sheet.
 
The row reads left to right as: sheet pill, then `[+]`, then the existing sheet delete `[×]`.
 
---
 
### 2.2 Layout — Chained Sheet Row
 
When a sheet has one or more chain links added to it, the row stays on a single horizontal line. The pills are laid out inline from left to right. Between each pill there is a short dash separator `—` to visually connect them. Each individual pill has its own small `[×]` directly beside it. After the last pill in the chain comes the `[+]` to add another link, and at the far right is the existing sheet-level delete `[×]`.
 
Using the example from the brief, a file with two sheets where one of them has a chain looks like this:
 
```
file 1                                                            [remove]
  sheet1 · T [×]  —  sheet2 · T [×]  [+]                        [×]
  sheet3 · D  [+]                                                 [×]
```
 
The small `[×]` next to each pill is the chain link remove. It only removes that specific link. The large `[×]` at the far right of the row is the existing sheet delete and removes the whole row and its entire chain. These are visually distinct — the chain link removes should be noticeably smaller and more muted than the sheet delete.
 
---
 
### 2.3 Chain Link Remove — Behaviour
 
When the user clicks the small `[×]` on any pill inside a chained row, a confirmation dialog must appear before anything is removed. The dialog should name the specific sheet being removed so the user is clear on what will be deleted.
 
On confirmation, only that link is removed from the chain. The remaining links stay in place and their order is recompacted. If the removal leaves only one pill on the row (just the original sheet with no more links), the row collapses back to a normal unchained state, `is_chained` is set to false, and the merged CSV output is regenerated or reverted accordingly. On cancel, nothing changes.
 
The first pill in a chained row — the original sheet that the chain was built from — can also have its chain link `[×]` clicked. In that case the behaviour depends on how many links remain. If there are other links in the chain, removing the first pill promotes the next pill in order to become the new primary, and the chain is regenerated with the new primary's columns as the locked reference. If it is the only remaining link, the row simply reverts to a normal unchained state. A confirmation dialog is shown either way.
 
---
 
### 2.4 The `[+]` Button — Behaviour
 
Clicking `[+]` on any sheet row opens a file browser filtered to xlsx files. After the user selects a file, the existing sheet selector dialog opens so they can pick which sheet from that file to chain. Once a sheet is selected, the app navigates to Screen 1.5 (the Chain Column Mapper). If the user cancels at any point during file browsing or sheet selection, nothing changes and the user stays on Screen 1.
 
---
 
### 2.5 Styling Notes
 
The chain link remove buttons must be visually smaller and more muted than the existing sheet-level delete so the hierarchy is immediately clear. In their default state they should appear in a subdued grey. On hover they should shift to a warning red to signal destructive intent. The `[+]` button should use the app's blue accent colour with a border outline, and disabled state (grey, no border) for when a sheet has not been fully loaded yet. The existing sheet-level delete style is not modified.
 
---

## Section 3 — Chain Column Mapper Screen (Screen 1.5)

**Goal:** Build the intermediate screen where the user maps columns from secondary file to primary file.

### 3.1 Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│  [ ← Back ]        Chain Columns                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────┐  ┌──────────────────────────┐    │
│  │  file1.xlsx (Primary)│  │  file2.xlsx              │    │
│  │  ─────────────────── │  │  ──────────────────────  │    │
│  │  □ Date         🔒   │  │  [TransactionDate ▾]     │    │
│  │  □ Amount       🔒   │  │  [Amt             ▾]     │    │
│  │  □ VendorID     🔒   │  │  [Vendor_ID       ▾]     │    │
│  │  □ Region       🔒   │  │  [Region          ▾]     │    │
│  └──────────────────────┘  └──────────────────────────┘    │
│                                                             │
│  ─── Rules ────────────────────────────────────────────     │
│  • Primary file columns are locked                          │
│  • Each secondary column can only be mapped once           │
│  • Auto-matched by name similarity on load                  │
│                                                             │
│                              [ Cancel ]  [ Confirm Chain ]  │
└─────────────────────────────────────────────────────────────┘
```

Left panel remains unchanged (same as Screen 1 — just the main area changes).

### 3.2 Column Pair Row Widget

```python
class ColumnPairRow(QWidget):
    def __init__(self, primary_col: str, secondary_cols: list[str], auto_match: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)

        # Left — locked primary column name
        primary_label = QLabel(primary_col)
        primary_label.setFixedWidth(220)
        primary_label.setStyleSheet("color: #9ca3af;")  # dimmed = locked
        lock_icon = QLabel("🔒")
        lock_icon.setFixedWidth(20)

        # Right — secondary column dropdown
        self.combo = QComboBox()
        self.combo.addItem("— Not Mapped —", userData=None)
        for col in secondary_cols:
            self.combo.addItem(col, userData=col)

        # Auto-select best match
        if auto_match:
            idx = self.combo.findText(auto_match)
            if idx >= 0:
                self.combo.setCurrentIndex(idx)

        layout.addWidget(primary_label)
        layout.addWidget(lock_icon)
        layout.addStretch()
        layout.addWidget(self.combo, 1)
```

### 3.3 Auto-Match Logic

```python
def auto_match_columns(primary_cols: list[str], secondary_cols: list[str]) -> dict:
    """Returns {primary_col: best_secondary_col or None}"""
    from difflib import get_close_matches
    mapping = {}
    used = set()
    for col in primary_cols:
        # Exact match first (case-insensitive)
        exact = next((s for s in secondary_cols if s.lower() == col.lower() and s not in used), None)
        if exact:
            mapping[col] = exact
            used.add(exact)
        else:
            # Fuzzy match
            matches = get_close_matches(col.lower(), [s.lower() for s in secondary_cols if s not in used], n=1, cutoff=0.6)
            if matches:
                matched = next(s for s in secondary_cols if s.lower() == matches[0] and s not in used)
                mapping[col] = matched
                used.add(matched)
            else:
                mapping[col] = None
    return mapping
```

### 3.4 Duplicate Column Validation

Track which secondary columns are selected across all rows. When the user changes a combo:

```python
def _on_combo_changed(self):
    selected = [row.combo.currentData() for row in self.rows if row.combo.currentData()]
    seen = set()
    for row in self.rows:
        val = row.combo.currentData()
        if val in seen:
            row.combo.setStyleSheet("border: 1px solid #ef4444;")  # red border = duplicate
        else:
            row.combo.setStyleSheet("")
        if val:
            seen.add(val)
    self._update_confirm_button()
```

The **Confirm** button is disabled if any duplicate selection exists.

### 3.5 Confirm Action

```python
def _on_confirm(self):
    column_map = {}
    for col, row in zip(self.primary_cols, self.rows):
        secondary_val = row.combo.currentData()
        if secondary_val:
            column_map[col] = secondary_val
        # Unmapped cols are simply absent — they'll be NaN in the output

    self.chain_confirmed.emit(self.sheet_id, ChainEntry(
        order=len(current_chain),
        file_path=self.secondary_file_path,
        sheet_name=self.secondary_sheet_name,
        file_label=os.path.basename(self.secondary_file_path),
        column_map=column_map
    ))
```

Emits `chain_confirmed` signal → parent saves the entry → navigates back to Screen 1.

---

## Section 4 — Navigation & State Management

**Goal:** Ensure forward/back navigation works cleanly and state is preserved.

### 4.1 Frame Stack

CleanSheet uses frame-switching (not re-renders). Add Screen 1.5 as a registered frame:

```python
# In main_window.py
self.frames = {
    "launcher":      LauncherScreen(self),
    "data_loader":   DataLoaderScreen(self),
    "chain_mapper":  ChainMapperScreen(self),   # NEW
    "mapper":        MapperScreen(self),
    "workspace":     WorkspaceScreen(self),
}
```

### 4.2 Navigation Flow

```
DataLoader (Screen 1)
    → user clicks [+] on a sheet pill
    → browse file + select sheet
    → main_window.show_frame("chain_mapper", context={...})

ChainMapper (Screen 1.5)
    → user clicks [Confirm Chain]
    → emits chain_confirmed signal
    → main_window receives → updates project state → show_frame("data_loader")

    → user clicks [← Back] / [Cancel]
    → main_window.show_frame("data_loader")  ← no state change
```

### 4.3 Context Passing to ChainMapper

```python
def show_chain_mapper(self, sheet_id, secondary_file, secondary_sheet):
    ctx = {
        "sheet_id": sheet_id,
        "primary_entry": self.project.get_chain_primary(sheet_id),  # ChainEntry order=0
        "secondary_file": secondary_file,
        "secondary_sheet": secondary_sheet,
    }
    self.frames["chain_mapper"].load_context(ctx)
    self.show_frame("chain_mapper")
```

### 4.4 Project State Update on Confirm

```python
def on_chain_confirmed(self, sheet_id: str, new_entry: ChainEntry):
    self.project.append_chain_entry(sheet_id, new_entry)
    self.project.save()
    self.frames["data_loader"].refresh_sheet_pills()
    self.show_frame("data_loader")
```

---

## Section 5 — CSV Output & Metadata

**Goal:** Write the unified CSV and ensure metadata is persisted correctly.

### 5.1 When is the CSV Written?

The unified CSV is (re)written whenever:
1. The user confirms a new chain link (incremental — append new file's rows).
2. The user edits a chain mapping and re-confirms.
3. The project is saved explicitly.

**Recommended:** Write on confirm (so the output is always fresh and matches current mappings).

### 5.2 CSV Output Structure

```
Date, Amount, VendorID, Region, source
2024-01-01, 100.0, V001, North, file1.xlsx
2024-01-02, 200.0, V002, South, file1.xlsx
2024-01-01, 150.0, V001, North, file2.xlsx   ← remapped from TransactionDate, Amt, Vendor_ID
```

`source` is always the **last column**.

### 5.3 Handling Unmapped Columns

If a primary column has no mapping in a secondary file (user selected "— Not Mapped —"), those rows will have `NaN` / empty string for that column. This is valid — do not error.

### 5.4 Metadata in Project Manifest

After `chain_writer.write_chained_csv(...)` completes, update `project.json`:

```python
sheet_record["is_chained"] = True
sheet_record["chain"] = [entry.to_dict() for entry in chain_entries]
sheet_record["output_csv"] = output_csv_path
project.save()
```

This metadata is the contract for future screens to know how to handle this table differently.

---

## Section 6 — Edge Cases & Validation Rules

**Goal:** Document all guard conditions so each session's implementer knows the boundaries.

| # | Condition | Behaviour |
|---|-----------|-----------|
| 1 | User clicks `[+]` on a Dimension table | Allowed — chaining works for both T and D types |
| 2 | Secondary file has fewer columns than primary | Only mapped columns are pulled; others are NaN |
| 3 | Secondary file has more columns than primary | Extra columns are ignored |
| 4 | User maps same secondary col to two primary cols | Confirm button disabled, red highlight on duplicate |
| 5 | User cancels on ChainMapper | No state change; return to DataLoader |
| 6 | User removes a chain link (future) | Out of scope for this feature — note: not currently implemented |
| 7 | Primary file has 0 columns loaded | Should not reach ChainMapper — blocked upstream at sheet load |
| 8 | Secondary file is same path+sheet as primary | Show warning: "Cannot chain a sheet with itself" |
| 9 | Chain has 3+ files | Each `[+]` adds one more link; no maximum defined |
| 10 | Project reopened with existing chain | Load `chain` array from manifest and reconstruct pill display |

---

## Section 7 — QSS Styling Tokens

All new widgets must use existing CleanSheet design tokens.

```css
/* Chain add button */
QPushButton#chainAddBtn {
    background: transparent;
    border: 1px solid #3b82f6;
    border-radius: 4px;
    color: #3b82f6;
    font-size: 13px;
    padding: 0px 4px;
}
QPushButton#chainAddBtn:hover {
    background: #1e3a5f;
}

/* Chain separator label */
QLabel#chainSeparator {
    color: #6b7280;
    font-size: 12px;
    padding: 0 4px;
}

/* Locked primary column row */
QLabel#primaryColLocked {
    color: #4b5563;
}

/* Duplicate column highlight */
QComboBox#duplicateCol {
    border: 1px solid #ef4444;
}

/* Chain mapper panel background (same as existing surface) */
QWidget#chainMapperPanel {
    background: #13161e;
    border-radius: 8px;
}
```

---

## Session Breakdown (Recommended Order)

| Session | Section(s) | Deliverable |
|---------|------------|-------------|
| A | Section 1 | `models/chain_entry.py`, `services/chain_writer.py`, update project manifest schema |
| B | Section 2 | `SheetPillWidget` with `[+]` button and chain separator display |
| C | Section 3 | `ChainMapperScreen` widget (Screen 1.5) — column pair rows, auto-match, validation |
| D | Section 4 | Navigation wiring in `main_window.py`, context passing, confirm/cancel signals |
| E | Section 5–6 | CSV write-on-confirm, metadata persistence, edge case guards |
| F | Section 7 | QSS pass — apply tokens, test visual consistency with rest of app |

Each session should be given: this spec file, the master HTML visual, and `UI_SPEC_V2.md`.
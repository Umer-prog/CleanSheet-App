# CleanSheet Bug Report & Feature Spec

## How to Use This Document
Hand this to a fresh Claude Code session alongside `UI_SPEC_V2.md` and the master HTML visual. Each issue is self-contained. Work one issue per session.

---

## Issue 1 — Screen 1→1.5→Chainer: Threading, Render Glitch, Transition Glitch

### Problem
Three related problems in the navigation flow from Screen 1 (file picker) to Screen 1.5 (Chain Column Mapper loader) to the Chainer screen:

1. **No threading on data load** — The transition from Screen 1.5 to the Chainer screen loads data on the main thread, blocking the UI and causing visible slowness/freeze.
2. **Render glitch — floating box** — A box artifact appears in the top-left of the screen (approximately 30% of app width) during the loading phase only. Disappears once load completes.
3. **Transition glitch** — The screen transition itself is visually broken (flash, jump, or partial render).

### Root Cause Hypotheses
- The Chainer screen's `__init__` or `setup_ui()` is calling data-loading logic synchronously before the widget is fully painted.
- A placeholder widget or layout spacer is being made visible before its parent container is ready, producing the floating box.
- The transition likely calls `show()` on the new screen before `hide()` on the old one completes, or triggers a repaint mid-construction.

### How to Fix

**Threading:**
- Wrap the data-loading step (reading parquet files, building the chain column model) inside a `QThread` worker.
- Show a spinner or loading state in Screen 1.5 while the worker runs.
- Only emit the signal to transition to the Chainer screen from the worker's `finished` signal.
- Pattern to follow: look at how other screens in the app already use `QThread` for parquet loads — replicate that pattern here.

**Floating box glitch:**
- Audit Screen 1.5 and the Chainer screen's `setup_ui()` for any widget that is instantiated but not yet populated (e.g. a `QFrame`, `QGroupBox`, or `QStackedWidget` panel that renders empty before data arrives).
- Either hide that widget (`widget.setVisible(False)`) until the worker finishes, or delay its construction until after data is ready.
- Check layout stretch factors — a zero-content widget with a background stylesheet will render as a visible empty box.

**Transition glitch:**
- Ensure the sequence is: worker finishes → new screen fully constructed and populated → old screen hidden → new screen shown.
- Do not call `show()` on the Chainer screen until all `setup_ui()` and initial data binding is complete.
- If using a `QStackedWidget`, call `setCurrentWidget()` only after the incoming screen emits a ready signal.

---

## Issue 2 — Scroll-over Changes Dropdown Value

### Problem
Throughout the app, hovering or scrolling the mouse wheel over a `QComboBox` while the dropdown is closed changes its selected value. This causes accidental value changes when the user scrolls the page.

### How to Fix
Subclass `QComboBox` (or apply an event filter globally) to suppress `WheelEvent` when the widget does not have focus.

```
Create a custom subclass, e.g. NoScrollComboBox(QComboBox).
Override wheelEvent: if not self.hasFocus(), ignore the event and return.
Replace all QComboBox usages in the codebase with NoScrollComboBox.
```

This is a one-file change (define the subclass in a shared widgets file) plus a find-and-replace across the UI layer. Do not change any business logic.

---


### Issue 3 — Dimension Table: Duplicate Value Warning Instead of Hard Block
### Problem
The dimension table is incorrectly blocking rows where a column value (e.g. Export) already exists in that column, even when the full row is not a duplicate.
Example of what should be allowed:

Africa → Export exists
User adds Germany → Export → should be allowed (different row, shared column value)

### Example of what should be blocked:

Africa → Export exists
User adds Africa → Export again → exact duplicate, block it

Currently the app is treating a shared column value as a duplicate, which is wrong.
### Desired Behavior
ScenarioActionEntire row is identical to an existing rowHard block — do not allowOnly a column value is shared (e.g. same region, different country)Allow freely, no warningA column value appears frequently and user adds yet another row sharing itAllow freely, no warning
No warning dialog needed. The rule is simple: duplicate = all columns match. Partial matches on any single column are not duplicates and must never be blocked or warned.
### How to Fix

Find the duplicate validation function for the dimension table.
Change the comparison to check the entire row as a composite key, not individual column values in isolation.
A row is a duplicate only when every column value matches an existing row exactly.
Remove any per-column uniqueness constraint that is not intentionally part of the spec.
No dialog needed — just unblock the false positive cases.
---

## Issue 4 — Screen 3: Mapping Status Shows Wrong Icon (Render Glitch)

### Problem
The mapping status indicator in Screen 3 (tick/error icon per column) sometimes shows an error icon even though the mapping is actually valid. Clicking the row or refreshing reveals the correct tick. This is a rendering/state sync issue, not a logic issue — the underlying mapping data is correct.

### Root Cause Hypothesis
The status icon is being set during an intermediate state (e.g. before the mapping validation pass completes, or during a partial repaint of the table/list). The model's data and the delegate's rendered output are out of sync.

### How to Fix
- Find where the mapping status icon is assigned in the delegate or model for Screen 3.
- Ensure that `dataChanged` is emitted on the model **after** the full validation pass completes, not per-row during the pass.
- If the icon is set via a `QStyledItemDelegate`, confirm that `painter.restore()` is being called correctly and no state leaks between rows.
- Add a single `model.layoutChanged.emit()` or `viewport().update()` call at the end of the full validation cycle rather than mid-loop.
- Do not change the validation logic itself — only the timing of the repaint signal.

---

## Issue 5 — Screen 3 Append to Chain: Do Not Re-read Existing Sources from Disk

### Problem
When a user appends a new sheet to an existing chain (transaction or dimension table, Screen 3 only), the app re-reads all original source files from disk for all sheets already in the chain. This causes previously resolved errors to reappear because the raw source files still contain the original dirty data.

### Desired Behavior
- **First-time chain creation**: read all sheets from their source files on disk. Normal behavior, no change.
- **Append to existing chain (Screen 3 only)**: load the existing chain data from the **current history commit** (parquet), then read only the newly appended sheet from disk and merge it in. Do not re-read previously chained sheets from their source files.

### How to Fix

**Detect the append case:**
The code path for "append to chain" must be distinguishable from "create chain." Likely already a separate function or branch — confirm this.

**Load existing chain from history:**
- In the append code path, before reading any files, load the current committed parquet for that chain (transaction or dimension) from `metadata/` → active commit → relevant subfolder.
- This parquet represents the already-cleaned state of the existing sheets.

**Read only the new sheet:**
- Read only the newly selected xlsx/sheet from disk.
- Apply the same column normalization and source-tagging logic that runs during first-time chain creation.

**Merge and save:**
- `pd.concat([existing_parquet_df, new_sheet_df], ignore_index=True)`
- Write the result back to a new commit snapshot as normal.

**Scope guard:**
This change applies **only** to Screen 3's append flow. The first-time chain creation flow (Screen 1 → 1.5 → Chainer) must not be affected. Add a clear comment in code marking this distinction.

---

## Summary Table

| # | Area | Type | Effort |
|---|------|------|--------|
| 1 | Screen 1→1.5→Chainer | Threading + 2× render bugs | High |
| 2 | All dropdowns | UX / event filter | Low |
| 3 | Dimension table | Validation logic + dialog | Low |
| 4 | Screen 3 mapping icons | Render/repaint timing | Medium |
| 5 | Screen 3 append chain | Data loading logic | High |




Issue 1 (Partial Fix) — Floating Loader Box + Scroll Glitch Still Present
What Was Fixed
Threading was added — load speed improved. ✓
What Is Still Broken
Bug A — Floating loader box
The "Loading columns..." spinner widget is rendering in the top-left of the content area instead of being centered. See screenshot — the box sits detached at roughly the top-left quadrant of the main panel, not in the middle of the screen.
Root cause to look for:

The loader widget is likely being added to a layout that hasn't been given center alignment, or it's being placed directly into a parent with absolute/no layout, defaulting to (0,0).
Or the loader is a child of the left panel / sidebar container instead of the main content area.

Fix:

Find where the loading spinner/widget is constructed and inserted into the layout.
Ensure it lives inside the main content panel, not the sidebar or a bare parent widget.
Wrap it in a layout with Qt.AlignCenter:

layout.addWidget(loader_widget, alignment=Qt.AlignCenter)

Or if using absolute positioning, compute center: x = (parent.width() - widget.width()) / 2
After threading finishes and the real content loads, call loader_widget.setVisible(False) before showing the populated screen.


Bug B — Scroll wheel still changes QComboBox value on Screen 1.5
The NoScrollComboBox fix either was not applied to Screen 1.5's dropdowns, or the dropdowns on that screen are still using plain QComboBox.
Fix:

Confirm that the NoScrollComboBox subclass exists in the shared widgets file.
Search specifically in the Screen 1.5 file for any QComboBox( instantiation and replace with NoScrollComboBox(.
Also check if Screen 1.5 uses a delegate that creates comboboxes inside a QTableView or QListView — if so, the delegate's createEditor method must also return NoScrollComboBox instead of QComboBox.


How to Verify Both Fixes

Box fix: Navigate to Screen 1.5 while loading — spinner should appear centered in the content panel, not floating top-left.
Scroll fix: On Screen 1.5, hover over any dropdown without clicking it, scroll the mouse wheel — value must not change.
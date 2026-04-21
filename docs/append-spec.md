
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

 
The left panel stays exactly as it is on Screen 1 — no changes.add a small chain step like other  steps. Only the main content area changes. The main area shows two side-by-side panels. The left panel is headed with the primary file's name and marked as primary. The right panel is headed with the secondary file's name. Below each header is a scrollable list of mapping rows. Below the two panels there is a short rules reminder visible at all times, and at the bottom right are a Cancel button and a Confirm Chain button.
 
### 3.2 Mapping Rows — Primary Columns
 
For each column that exists in the primary file, there is one mapping row. The left side of the row shows the primary column name, styled as locked and dimmed so it is clearly not editable. The right side shows a dropdown listing all columns from the secondary file plus a "Not Mapped" option at the top of the list. The user selects which secondary column corresponds to this primary column, or leaves it as Not Mapped if there is no equivalent.
 
### 3.3 Mapping Rows — Extra Secondary Columns
 
For every column in the secondary file that was not selected in any mapping row above, an additional row is appended below the primary-matched rows. These rows are informational only. The left side is blank or shows a placeholder to indicate no primary equivalent exists. The right side shows the secondary column name as a fixed non-editable label. These rows cannot be interacted with and simply inform the user that this column exists in the secondary file and will appear in the output with empty values for all other sources.
 
### 3.4 Auto-Match on Load
 
When the screen opens, all dropdowns should be pre-filled using automatic column matching. The matching logic should first attempt an exact case-insensitive comparison between each primary column name and each secondary column name. If no exact match is found it should fall back to fuzzy similarity. A secondary column that has already been matched to one primary column must not be auto-matched to another. Any primary column with no match defaults to Not Mapped.
 
### 3.5 Duplicate Validation
 
The same secondary column must not be selected in more than one dropdown simultaneously. Whenever the user changes any dropdown, the implementation should check all selections for duplicates. Any dropdown that holds a duplicated value should be visually flagged with a red border. The Confirm Chain button must remain disabled for as long as any duplicate exists.
 
### 3.6 Confirm and Cancel
 
On Cancel the screen returns to Screen 1 with no changes to the project state whatsoever. On Confirm Chain the current mapping state is saved into the chain entry for this secondary file, the project is saved, and the screen returns to Screen 1 where the sheet row now reflects the newly added chain link.
 
---
 
## Section 4 — Navigation & State Management
 
**Goal:** Describe how Screen 1.5 fits into the existing frame-switching navigation and what state must be passed in and out of it.
 
### 4.1 Registering the New Screen
 
Screen 1.5 must be registered as a named frame in the main window alongside all existing screens. The app already uses frame-switching rather than full re-renders, so the chain mapper screen follows the same pattern. It is instantiated once at startup and shown or hidden as needed.
 
### 4.2 Entering Screen 1.5
 
The transition into Screen 1.5 is always triggered from Screen 1 after the user has completed file browsing and sheet selection. Before switching frames, the main window must pass the following context into the chain mapper screen: the sheet ID of the sheet being chained onto, the full column list of the current primary entry for that sheet, the file path of the newly selected secondary file, and the sheet name selected from that file. The chain mapper screen uses this context to load the primary columns on the left side and the secondary columns in the dropdowns on the right side.
 
### 4.3 Exiting Screen 1.5
 
There are two exit paths. On Cancel, the main window switches back to Screen 1 and the chain mapper's context is cleared. No project state is written. On Confirm Chain, the chain mapper passes the completed mapping back to the main window, which appends the new chain entry to the relevant sheet record, saves the project, refreshes the affected sheet row in Screen 1's panel, and then switches back to Screen 1.
 
### 4.4 No Back-Stack Required
 
Screen 1.5 only ever comes from Screen 1 and only ever returns to Screen 1. There is no deeper navigation from within it. Cancel and Confirm are the only two exits. A back button in the header can be treated as equivalent to Cancel.
 
---
 
## Section 5 — CSV Column Rules & Output
 
**Goal:** Define precisely how the unified CSV is structured given the updated column rules where secondary files can contribute extra columns.
 
### 5.1 Column Order in the Output
 
The unified CSV columns are ordered as follows. First come all columns from the primary file in their original order. After those come any extra columns that exist in one or more secondary files but were not mapped to any primary column, in the order they are first encountered across the chain entries. The `source` column is always last.
 
### 5.2 Primary File Rows
 
Rows from the primary file include values for all primary columns as-is. For any extra columns that came from secondary files and have no equivalent in the primary, the primary rows leave those cells empty.
 
### 5.3 Secondary File Rows
 
Rows from a secondary file have their mapped columns renamed to match the corresponding primary column names. Any primary columns that the secondary file has no mapping for are left empty for those rows. Any extra columns that this secondary file contributes are filled with their actual values. Extra columns that belong to a different secondary file and not this one are left empty for these rows.
 
### 5.4 When the CSV is Written
 
The unified CSV is written every time the user confirms a chain link addition or a chain link removal. It is not written lazily — it must always reflect the current chain state immediately after any change. If the chain collapses back to a single entry, the output reverts to a plain CSV without the `source` column and without any extra secondary columns, matching the format of a normal non-chained sheet.
 
### 5.5 Metadata Persistence
 
After the CSV is written, the project manifest must be updated to reflect the current chain state. The sheet record's chained flag, the full chain entry list, and the output CSV path must all be saved together in the same write operation so they are never out of sync. The chained flag is the field downstream screens rely on to know they are dealing with a chained table.
 
---
 
## Section 6 — Edge Cases & Validation Rules
 
**Goal:** Document all guard conditions so each session's implementer knows the boundaries.
 
| # | Condition | Behaviour |
|---|-----------|-----------|
| 1 | User clicks `[+]` on a Dimension table | Allowed — chaining works for both T and D types |
| 2 | Secondary file has fewer columns than primary | Only mapped columns are pulled; others are NaN |
| 3 | Secondary file has more columns than primary | Extra columns are included in the unified output; rows from sources that do not have those columns are left empty for them |
| 4 | User maps same secondary col to two primary cols | Confirm button disabled, red highlight on duplicate |
| 5 | User cancels on ChainMapper | No state change; return to DataLoader |
| 6 | User removes the only secondary link (chain collapses to 1 file) | `is_chained` → False, `chain` → null, revert output CSV to single-source (no `source` column) |
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
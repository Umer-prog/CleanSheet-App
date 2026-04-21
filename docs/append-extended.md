# Sheet Chaining — Extension Spec: Sources Dialog (Screen 3)
**CleanSheet | Extension to: SHEET_CHAINING_SPEC.md**
**Scope: Transaction Sources and Dimension Sources panels on Screen 3**

---

## Overview

This extension covers changes to the Transaction Sources and Dimension Sources sections on Screen 3 that are needed to support chained tables. The core chaining logic and data model are already defined in the main spec. This document only describes what changes on Screen 3 and what stays the same.

Unchained sources remain completely untouched. Chained sources get a new grouped visual treatment and a different set of available actions compared to unchained sources. The refresh button behaviour for chained sources will be covered in a separate spec.

---

## Section 1 — Unchained Sources

No changes. Single unchained sources continue to display exactly as they do today with all their existing buttons intact. This section exists only to make it explicit that nothing about them is modified.

---

## Section 2 — Chained Sources — Grouped Display

### 2.1 Visual Grouping

When a source is chained, its entries must be displayed as a group rather than as flat independent rows. The primary entry sits at the top of the group and is the visual anchor. Each additional chain link appears directly below it, indented to show it is a subordinate member of the group. The grouping is strictly vertical.

Using a concrete example, a chained transaction table with two links would look like this:

```
purchase_fact  [delete]  [append]  [refresh]
  └ file2.xlsx · Sheet1
  └ file3.xlsx · Transactions
```

The group should be visually separated from other sources above and below it by a slightly larger gap or a subtle divider so it reads as a single unit rather than individual rows.

### 2.2 Primary Row

The primary row shows the table label as it does today for unchained sources. The action buttons available on a chained primary are delete, append, and refresh only. There is no replace button on a chained source. These three buttons are the only controls on the primary row.

### 2.3 Sub-rows

Each chain link sub-row shows the file label and sheet name of that entry. Sub-rows have no action buttons of any kind. They are read-only display rows whose only purpose is to inform the user which files make up this grouped source. They should be visually muted relative to the primary row to reinforce that they are not independently actionable.

---

## Section 3 — Append Button

### 3.1 Placement and Visibility

The append button only appears on the primary row of a chained source. It does not appear on unchained sources and does not appear on sub-rows.

### 3.2 Behaviour

Clicking append opens a file browser filtered to xlsx files. After the user selects a file, the existing sheet selector dialog opens so they can pick a sheet from that file. Once a sheet is selected, the app navigates to Screen 1.5 (the Chain Column Mapper) with the existing chain's primary column list as the locked left side and the newly selected sheet's columns on the right side. This is the same Screen 1.5 flow defined in the main spec.

On confirm in Screen 1.5, the new chain entry is appended to the chain, the unified CSV is regenerated, the project is saved, and the user is returned to Screen 3 with the source list refreshed to show the new sub-row. On cancel at any point during file browsing, sheet selection, or on Screen 1.5, nothing changes and the user is returned to Screen 3 without any modification.

### 3.3 Return Destination After Screen 1.5

The append flow here originates from Screen 3, not from Screen 1. After Screen 1.5 confirm or cancel, the app must return the user to Screen 3, not to Screen 1. The source list on Screen 3 should reflect the updated chain state when the user arrives back.

---

## Section 4 — Delete Button on Chained Primary

The delete button on a chained primary removes the entire grouped source — the primary and all its chain links together. A confirmation dialog must be shown before anything is deleted, and it should make clear that all chain links will be removed along with the primary. The confirmation wording should be noticeably different from the standard single-source delete to avoid the user accidentally discarding a multi-file chain. On confirm, the entire source and its chain are removed from the project and the CSV output is deleted. On cancel, nothing changes.

---

## Section 5 — Refresh Button on Chained Primary

The refresh button is noted here as a placeholder. Its full behaviour for chained sources will be defined in a separate spec. The button should be present and visible on the primary row but its specific action for chained tables is out of scope for this document.

---

## Section 6 — Add File Button

The existing add file button at the top of the sources section currently adds a new source within Screen 3. This button should now navigate the user to Screen 1 (the Data Loader) instead, since Screen 1 is the canonical place for loading new files and defining new sources whether chained or not. Navigating away via this button does not save or discard any pending state on Screen 3 beyond what is already persisted.

---

## Section 7 — Edge Cases

| # | Condition | Behaviour |
|---|-----------|-----------|
| 1 | Chained source has only the primary remaining (all links removed via Screen 1) | `is_chained` is false so it renders as a normal unchained row with standard buttons; append is not shown |
| 2 | User clicks append, cancels at file browser | Returns to Screen 3, no change |
| 3 | User clicks append, cancels at sheet selector | Returns to Screen 3, no change |
| 4 | User clicks append, cancels on Screen 1.5 | Returns to Screen 3, no change |
| 5 | User clicks delete on a chained primary | Confirmation dialog names all chain links; on confirm entire group is removed; on cancel nothing changes |
| 6 | Project reopened with existing chain | Screen 3 reconstructs grouped display from chain entries in the manifest |
| 7 | User clicks Add File button | User is navigated to Screen 1 |


going from screen 3 to screen 1 cannot delete previous chains or sources it can only add.
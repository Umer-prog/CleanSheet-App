# UI Copy Review (Draft)

Only entries where the suggested text differs from the current text are included below.

## Copy principles
- Use sentence case (avoid ALL CAPS).
- Use specific, outcome-based dialog titles (avoid generic "Error").
- Say what happened in plain language, then give the user a next step.
- Keep labels/buttons short and consistent.
- If technical details are shown, label them (for example, "Details: ...").

## Heading spacing (Title + Subtext)

Some screens render the top-bar heading as two stacked labels (`title_lbl` + `meta_lbl`). Even with a small layout spacing, this can read as looser than the compact rich-text headings used elsewhere (title + subtext in a single `QLabel`).

**Recommendation**
- Prefer a single rich-text `QLabel` for title + subtext using `<span>` + `<br>` (avoid `<p>` tags because Qt adds default margins).
- If you keep two labels, keep `tb_text.setSpacing(0-2)` and ensure there are no extra margins/padding on either label.

**Suggested heading HTML pattern (matches existing sizes)**
```python
heading = QLabel(
    "<span style='color:#f1f5f9; font-size:15px; font-weight:600;'>Title</span>"
    "<br>"
    "<span style='color:#94a3b8; font-size:11px;'>Short supporting subtext.</span>"
)
```

**Where to apply (currently split title + meta labels)**
- `CleanSheet/ui/views/view_t_sources.py:112`
- `CleanSheet/ui/views/view_d_sources.py:185`
- `CleanSheet/ui/views/view_history.py:200`
- `CleanSheet/ui/views/view_settings.py:92`

## `CleanSheet/ui/app.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/app.py:147` | UI copy | Operation in Progress | Working... Please wait. | Rewrite for clarity. |

## `CleanSheet/ui/popups/popup_add.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/popups/popup_add.py:379` | UI copy | the transaction cell will also be updated to the new value automatically. | The transaction cell will also update to the new value. | Rewrite for clarity. |
| `CleanSheet/ui/popups/popup_add.py:499` | UI copy | Add Row to Dimension | Add Row To Dimension | Button labels in title case. |

## `CleanSheet/ui/popups/popup_replace.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/popups/popup_replace.py:228` | UI copy | replace with a valid dimension value | Choose a valid value from the dimension table | Rewrite for clarity. |
| `CleanSheet/ui/popups/popup_replace.py:252` | UI copy | DIMENSION TABLE | Dimension Table | Avoid all-caps headings. |

## `CleanSheet/ui/popups/popup_sheet_selector.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/popups/popup_sheet_selector.py:112` | UI copy | CHOOSE SHEETS AND ASSIGN CATEGORY | Choose Sheets And Assign Category | Avoid all-caps headings. |

## `CleanSheet/ui/popups/popup_single_sheet.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/popups/popup_single_sheet.py:169` | UI copy | HEADER ROW | Header Row | Avoid all-caps headings. |

## `CleanSheet/ui/screen0_launcher.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/screen0_launcher.py:340` | UI copy | SELECTED PROJECT | Selected Project | Avoid all-caps headings. |
| `CleanSheet/ui/screen0_launcher.py:693` | Dialog | Title: Error<br>Body: Could not open project:<br>{exc} | Title: Couldn't open project<br>Body: We couldn't open project.<br><br>Details: {exc}<br><br>Make sure the file exists, is a supported Excel file, and isn't open in Excel, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/screen0_launcher.py:719` | Dialog | Title: Error<br>Body: Could not delete project:<br>{exc} | Title: Couldn't delete project<br>Body: We couldn't delete project.<br><br>Details: {exc}<br><br>Make sure the item isn't in use, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/screen0_launcher.py:850` | UI copy | SAVE LOCATION | Save Location | Avoid all-caps headings. |
| `CleanSheet/ui/screen0_launcher.py:957` | UI copy | Could not create project: {exc} | We couldn't create project: {exc} | Use plain language; label technical details. |

## `CleanSheet/ui/screen15_chain_mapper.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/screen15_chain_mapper.py:203` | UI copy | SETUP PROGRESS | Setup Progress | Avoid all-caps headings. |

## `CleanSheet/ui/screen1_sources.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/screen1_sources.py:145` | UI copy | SETUP PROGRESS | Setup Progress | Avoid all-caps headings. |
| `CleanSheet/ui/screen1_sources.py:227` | UI copy | ← Back to Projects | ← Back To Projects | Button labels in title case. |
| `CleanSheet/ui/screen1_sources.py:313` | UI copy | LOADED FILES | Loaded Files | Avoid all-caps headings. |
| `CleanSheet/ui/screen1_sources.py:789` | Dialog | Title: Error<br>Body: Could not read Excel file:<br>{exc} | Title: Couldn't read Excel file<br>Body: We couldn't read Excel file.<br><br>Details: {exc}<br><br>Make sure the file exists, is a supported Excel file, and isn't open in Excel, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/screen1_sources.py:862` | Dialog | Title: Error<br>Body: Could not read Excel file:<br>{exc} | Title: Couldn't read Excel file<br>Body: We couldn't read Excel file.<br><br>Details: {exc}<br><br>Make sure the file exists, is a supported Excel file, and isn't open in Excel, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/screen1_sources.py:1007` | Dialog | Title: Error<br>Body: Could not save selected sheets:<br>{exc} | Title: Couldn't save selected sheets<br>Body: We couldn't save selected sheets.<br><br>Details: {exc}<br><br>Check the destination folder is writable and the output file isn't open, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |

## `CleanSheet/ui/screen2_mappings.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/screen2_mappings.py:165` | UI copy | SETUP PROGRESS | Setup Progress | Avoid all-caps headings. |
| `CleanSheet/ui/screen2_mappings.py:241` | UI copy | ← Back to Data Loader | ← Back To Data Loader | Button labels in title case. |
| `CleanSheet/ui/screen2_mappings.py:488` | UI copy | CONFIRMED MAPPINGS | Confirmed Mappings | Avoid all-caps headings. |
| `CleanSheet/ui/screen2_mappings.py:790` | Dialog | Title: Error<br>Body: Could not remove '{table_name}':<br>{exc} | Title: Couldn't remove '{table_name}'<br>Body: We couldn't remove '{table_name}'.<br><br>Details: {exc}<br><br>Make sure the item isn't in use, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/screen2_mappings.py:845` | Dialog | Title: Error<br>Body: Could not load dim table '{table_name}':<br>{exc} | Title: Couldn't load dim table '{table_name}'<br>Body: We couldn't load dim table '{table_name}'.<br><br>Details: {exc}<br><br>Make sure the file exists, is a supported Excel file, and isn't open in Excel, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/screen2_mappings.py:870` | Dialog | Title: Error<br>Body: Could not load transaction table '{table_name}':<br>{exc} | Title: Couldn't load transaction table '{table_name}'<br>Body: We couldn't load transaction table '{table_name}'.<br><br>Details: {exc}<br><br>Make sure the file exists, is a supported Excel file, and isn't open in Excel, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/screen2_mappings.py:1200` | Dialog | Title: Error<br>Body: Could not save mappings:<br>{exc} | Title: Couldn't save mappings<br>Body: We couldn't save mappings.<br><br>Details: {exc}<br><br>Check the destination folder is writable and the output file isn't open, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/screen2_mappings.py:1246` | Dialog | Title: Error<br>Body: Could not read existing mappings:<br>{exc} | Title: Couldn't read existing mappings<br>Body: We couldn't read existing mappings.<br><br>Details: {exc}<br><br>Make sure the file exists, is a supported Excel file, and isn't open in Excel, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |

## `CleanSheet/ui/screen3_main.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/screen3_main.py:206` | Dialog | Title: Error<br>Body: Could not load mappings:<br>{exc} | Title: Couldn't load mappings<br>Body: We couldn't load mappings.<br><br>Details: {exc}<br><br>Make sure the file exists, is a supported Excel file, and isn't open in Excel, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/screen3_main.py:349` | UI copy | WORKSPACE | Workspace | Avoid all-caps headings. |
| `CleanSheet/ui/screen3_main.py:375` | UI copy | ← Back to Launcher | ← Back To Launcher | Button labels in title case. |
| `CleanSheet/ui/screen3_main.py:410` | UI copy | MAPPINGS | Mappings | Avoid all-caps headings. |
| `CleanSheet/ui/screen3_main.py:690` | UI copy | Could not delete mapping:<br>{exc} | We couldn't delete mapping.<br><br>Details: {exc} | Use plain language; label technical details. |
| `CleanSheet/ui/screen3_main.py:784` | Dialog | Title: Error<br>Body: Could not refresh project:<br>{exc} | Title: Couldn't refresh project<br>Body: We couldn't refresh project.<br><br>Details: {exc}<br><br>Try reopening the project. If it keeps happening, open the log folder and share the error details. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/screen3_main.py:793` | Dialog | Title: Error<br>Body: Could not refresh project:<br>{exc} | Title: Couldn't refresh project<br>Body: We couldn't refresh project.<br><br>Details: {exc}<br><br>Try reopening the project. If it keeps happening, open the log folder and share the error details. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/screen3_main.py:802` | Dialog | Title: Error<br>Body: Could not refresh project:<br>{exc} | Title: Couldn't refresh project<br>Body: We couldn't refresh project.<br><br>Details: {exc}<br><br>Try reopening the project. If it keeps happening, open the log folder and share the error details. | Make the title specific. Use plain language; label technical details. Add a next step. |

## `CleanSheet/ui/views/view_d_sources.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/views/view_d_sources.py:191` | UI copy | Add new dimension tables here. Orphaned tables (no active mappings) | Add dimension tables here. Tables with no active mappings | Trim extra whitespace. Rewrite for clarity. |
| `CleanSheet/ui/views/view_d_sources.py:192` | UI copy | may be permanently deleted. | can be deleted. | Rewrite for clarity. |
| `CleanSheet/ui/views/view_d_sources.py:230` | UI copy | CURRENT DIMENSION TABLES | Current Dimension Tables | Avoid all-caps headings. |
| `CleanSheet/ui/views/view_d_sources.py:568` | Dialog | Title: Error<br>Body: Could not read file:<br>{exc} | Title: Couldn't read file<br>Body: We couldn't read file.<br><br>Details: {exc}<br><br>Make sure the file exists, is a supported Excel file, and isn't open in Excel, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/views/view_d_sources.py:616` | Dialog | Title: Error<br>Body: Could not delete source:<br>{exc} | Title: Couldn't delete source<br>Body: We couldn't delete source.<br><br>Details: {exc}<br><br>Make sure the item isn't in use, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/views/view_d_sources.py:636` | Dialog | Title: Error<br>Body: Could not load table:<br>{exc} | Title: Couldn't load table<br>Body: We couldn't load table.<br><br>Details: {exc}<br><br>Make sure the file exists, is a supported Excel file, and isn't open in Excel, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/views/view_d_sources.py:666` | UI copy | Could not delete dimension table:<br>{exc} | We couldn't delete dimension table.<br><br>Details: {exc} | Use plain language; label technical details. |

## `CleanSheet/ui/views/view_history.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/views/view_history.py:206` | UI copy | Select a commit to inspect its details, edit the label, or revert — | Select a snapshot to review, rename, or revert — | Trim extra whitespace. Rewrite for clarity. |
| `CleanSheet/ui/views/view_history.py:207` | UI copy | reverting restores transactions, dimension tables, and mappings together. | Reverting restores transactions, dimension tables, and mappings to that snapshot. | Rewrite for clarity. |
| `CleanSheet/ui/views/view_history.py:298` | UI copy | COMMIT DETAILS | Commit Details | Avoid all-caps headings. |
| `CleanSheet/ui/views/view_history.py:427` | Dialog | Title: Error<br>Body: Could not create snapshot:<br>{exc} | Title: Couldn't create snapshot<br>Body: We couldn't create snapshot.<br><br>Details: {exc}<br><br>Try again. If it keeps happening, check the log for more details. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/views/view_history.py:684` | UI copy | Could not revert:<br>{exc} | We couldn't revert.<br><br>Details: {exc} | Use plain language; label technical details. |

## `CleanSheet/ui/views/view_mapping.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/views/view_mapping.py:613` | UI copy | Add to Dimension | Add To Dimension | Button labels in title case. |
| `CleanSheet/ui/views/view_mapping.py:1148` | UI copy | Could not replace:<br>{exc} | We couldn't replace.<br><br>Details: {exc} | Use plain language; label technical details. |
| `CleanSheet/ui/views/view_mapping.py:1211` | UI copy | Could not add row:<br>{exc} | We couldn't add row.<br><br>Details: {exc} | Use plain language; label technical details. |
| `CleanSheet/ui/views/view_mapping.py:1371` | Dialog | Title: Error<br>Body: Could not delete row:<br>{exc} | Title: Couldn't delete row<br>Body: We couldn't delete row.<br><br>Details: {exc}<br><br>Make sure the item isn't in use, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/views/view_mapping.py:1417` | Dialog | Title: Export Failed<br>Body: Could not generate final file:<br>{exc} | Title: Couldn't generate final file<br>Body: We couldn't generate final file.<br><br>Details: {exc}<br><br>Check the destination folder is writable and the output file isn't open, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |

## `CleanSheet/ui/views/view_settings.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/views/view_settings.py:98` | UI copy | Update project details and history preference, then save to apply changes. | Update project details and history settings, then save. | Rewrite for clarity. |
| `CleanSheet/ui/views/view_settings.py:366` | UI copy | Could not save settings:<br>{exc} | We couldn't save settings.<br><br>Details: {exc} | Use plain language; label technical details. |

## `CleanSheet/ui/views/view_t_sources.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/views/view_t_sources.py:118` | UI copy | Upload new versions for existing tables, delete obsolete ones, | Replace existing files, remove tables you no longer need, | Trim extra whitespace. Rewrite for clarity. |
| `CleanSheet/ui/views/view_t_sources.py:119` | UI copy | or add new transaction tables. | or add new tables. | Rewrite for clarity. |
| `CleanSheet/ui/views/view_t_sources.py:163` | UI copy | CURRENT TRANSACTION TABLES | Current Transaction Tables | Avoid all-caps headings. |
| `CleanSheet/ui/views/view_t_sources.py:209` | UI copy | No transaction tables added yet. | No transaction tables yet. Add one to get started. | Rewrite for clarity. |
| `CleanSheet/ui/views/view_t_sources.py:547` | Dialog | Title: Error<br>Body: Could not read file:<br>{exc} | Title: Couldn't read file<br>Body: We couldn't read file.<br><br>Details: {exc}<br><br>Make sure the file exists, is a supported Excel file, and isn't open in Excel, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/views/view_t_sources.py:596` | Dialog | Title: Error<br>Body: Could not delete source:<br>{exc} | Title: Couldn't delete source<br>Body: We couldn't delete source.<br><br>Details: {exc}<br><br>Make sure the item isn't in use, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |

| `CleanSheet/ui/views/view_t_sources.py:667` | UI copy | Deleting '{table_name}' will also remove {count} mapping(s). Confirm? | Deleting '{table_name}' will also remove {count} mapping(s). Continue? | Rewrite for clarity. |


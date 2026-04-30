# UI Copy Review (Draft)

User-facing UI text found in `CleanSheet/ui/**`, with suggested improvements for clearer, more professional UX copy.

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

**Existing compact heading examples (already using HTML title + subtext)**
- `CleanSheet/ui/activation_screen.py:79`
- `CleanSheet/ui/screen0_launcher.py:728`
- `CleanSheet/ui/screen15_chain_mapper.py:193`
- `CleanSheet/ui/popups/popup_sheet_selector.py:81`
- `CleanSheet/ui/popups/popup_single_sheet.py:111`

## `CleanSheet/ui/activation_screen.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/activation_screen.py:194` | UI copy | CleanSheet — Licensed software | CleanSheet — Licensed software |  |
| `CleanSheet/ui/activation_screen.py:198` | UI copy | Exit | Exit |  |
| `CleanSheet/ui/activation_screen.py:317` | UI copy | Copy Machine ID | Copy Machine ID |  |
| `CleanSheet/ui/activation_screen.py:324` | UI copy | Copied | Copied |  |
| `CleanSheet/ui/activation_screen.py:325` | UI copy | Copy Machine ID | Copy Machine ID |  |

## `CleanSheet/ui/app.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/app.py:44` | UI copy | {APP_NAME} v{APP_VERSION} | {APP_NAME} v{APP_VERSION} | Trim extra whitespace. |
| `CleanSheet/ui/app.py:108` | UI copy | {APP_NAME} v{APP_VERSION} | {APP_NAME} v{APP_VERSION} |  |
| `CleanSheet/ui/app.py:147` | UI copy | Operation in Progress | Working? Please wait. | Rewrite for clarity. |

## `CleanSheet/ui/popups/msgbox.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/popups/msgbox.py:46` | UI copy | OK | OK |  |
| `CleanSheet/ui/popups/msgbox.py:49` | UI copy | Open Log Folder | Open Log Folder |  |

## `CleanSheet/ui/popups/popup_about.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/popups/popup_about.py:18` | UI copy | About {APP_NAME} | About {APP_NAME} |  |
| `CleanSheet/ui/popups/popup_about.py:44` | UI copy | <b>{APP_NAME}</b> | <b>{APP_NAME}</b> |  |
| `CleanSheet/ui/popups/popup_about.py:48` | UI copy | Version {APP_VERSION} | Version {APP_VERSION} |  |
| `CleanSheet/ui/popups/popup_about.py:104` | UI copy | © 2025 {COMPANY} | © 2025 {COMPANY} |  |
| `CleanSheet/ui/popups/popup_about.py:110` | UI copy | Close | Close |  |

## `CleanSheet/ui/popups/popup_add.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/popups/popup_add.py:290` | UI copy | Add to Dimension | Add to Dimension |  |
| `CleanSheet/ui/popups/popup_add.py:297` | UI copy | New row will be added to | New row will be added to | Trim extra whitespace. |
| `CleanSheet/ui/popups/popup_add.py:335` | UI copy | Error value: | Error value: |  |
| `CleanSheet/ui/popups/popup_add.py:338` | UI copy | (empty) | (empty) |  |
| `CleanSheet/ui/popups/popup_add.py:341` | UI copy | — pre-filled as the key column below | — pre-filled as the key column below |  |
| `CleanSheet/ui/popups/popup_add.py:379` | UI copy | the transaction cell will also be updated to the new value automatically. | The transaction cell will also update to the new value. | Rewrite for clarity. |
| `CleanSheet/ui/popups/popup_add.py:485` | UI copy | field{'s' if req_count != 1 else ''} must be filled before adding | field{'s' if req_count != 1 else ''} must be filled before adding | Trim extra whitespace. |
| `CleanSheet/ui/popups/popup_add.py:493` | UI copy | Cancel | Cancel |  |
| `CleanSheet/ui/popups/popup_add.py:499` | UI copy | Add Row to Dimension | Add Row To Dimension | Button labels in title case. |
| `CleanSheet/ui/popups/popup_add.py:520` | UI copy | {len(errors)} field{'s' if len(errors) != 1 else ''} | {len(errors)} field{'s' if len(errors) != 1 else ''} | Trim extra whitespace. |
| `CleanSheet/ui/popups/popup_add.py:521` | UI copy | {'have' if len(errors) != 1 else 'has'} errors — fix before adding | {'have' if len(errors) != 1 else 'has'} errors — fix before adding |  |
| `CleanSheet/ui/popups/popup_add.py:545` | UI copy | This exact row already exists in the dimension table — | This exact row already exists in the dimension table — | Trim extra whitespace. |
| `CleanSheet/ui/popups/popup_add.py:546` | UI copy | every column value matches an existing row. | every column value matches an existing row. |  |

## `CleanSheet/ui/popups/popup_replace.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/popups/popup_replace.py:156` | UI copy | Replace Value | Replace Value |  |
| `CleanSheet/ui/popups/popup_replace.py:163` | UI copy | Select the correct value from | Select the correct value from | Trim extra whitespace. |
| `CleanSheet/ui/popups/popup_replace.py:221` | UI copy | Current bad value: | Current bad value: |  |
| `CleanSheet/ui/popups/popup_replace.py:224` | UI copy | (empty) | (empty) |  |
| `CleanSheet/ui/popups/popup_replace.py:228` | UI copy | replace with a valid dimension value | Choose a valid value from the dimension table | Rewrite for clarity. |
| `CleanSheet/ui/popups/popup_replace.py:252` | UI copy | DIMENSION TABLE | Dimension Table | Avoid all-caps headings. |
| `CleanSheet/ui/popups/popup_replace.py:257` | UI copy | {len(self._dim_df)} rows | {len(self._dim_df)} rows |  |
| `CleanSheet/ui/popups/popup_replace.py:271` | UI copy | Search values... | Search values... |  |
| `CleanSheet/ui/popups/popup_replace.py:339` | UI copy | {len(full)} rows | {len(full)} rows |  |
| `CleanSheet/ui/popups/popup_replace.py:357` | UI copy | {visible} / {total} rows | {visible} / {total} rows |  |
| `CleanSheet/ui/popups/popup_replace.py:357` | UI copy | {total} rows | {total} rows |  |
| `CleanSheet/ui/popups/popup_replace.py:399` | UI copy | Search values... | Search values... |  |
| `CleanSheet/ui/popups/popup_replace.py:478` | UI copy | Will replace: | Will replace: |  |
| `CleanSheet/ui/popups/popup_replace.py:480` | UI copy | (empty) | (empty) |  |
| `CleanSheet/ui/popups/popup_replace.py:514` | UI copy | Cancel | Cancel |  |
| `CleanSheet/ui/popups/popup_replace.py:520` | UI copy | Apply Replace | Apply Replace |  |
| `CleanSheet/ui/popups/popup_replace.py:618` | UI copy | Dimension Table | Dimension Table |  |
| `CleanSheet/ui/popups/popup_replace.py:627` | UI copy | {self._dim_table}</span> | {self._dim_table}</span> |  |
| `CleanSheet/ui/popups/popup_replace.py:628` | UI copy | · {row_count:,} rows | · {row_count:,} rows | Trim extra whitespace. |
| `CleanSheet/ui/popups/popup_replace.py:679` | UI copy | Close | Close |  |

## `CleanSheet/ui/popups/popup_revert_confirm.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/popups/popup_revert_confirm.py:80` | UI copy | Confirm Revert | Confirm Revert |  |
| `CleanSheet/ui/popups/popup_revert_confirm.py:88` | UI copy | {manifest_id}</span> | {manifest_id}</span> |  |
| `CleanSheet/ui/popups/popup_revert_confirm.py:131` | UI copy | This will restore transaction data to the selected snapshot.<br> | This will restore transaction data to the selected snapshot.<br> |  |
| `CleanSheet/ui/popups/popup_revert_confirm.py:132` | UI copy | Newer snapshots will remain in history but data will be rolled back. | Newer snapshots will remain in history but data will be rolled back. |  |
| `CleanSheet/ui/popups/popup_revert_confirm.py:155` | UI copy | Cancel | Cancel |  |
| `CleanSheet/ui/popups/popup_revert_confirm.py:166` | UI copy | Revert | Revert |  |

## `CleanSheet/ui/popups/popup_sheet_selector.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/popups/popup_sheet_selector.py:36` | UI copy | Select Sheets | Select Sheets |  |
| `CleanSheet/ui/popups/popup_sheet_selector.py:82` | UI copy | <br> | <br> |  |
| `CleanSheet/ui/popups/popup_sheet_selector.py:112` | UI copy | CHOOSE SHEETS AND ASSIGN CATEGORY | Choose Sheets And Assign Category | Avoid all-caps headings. |
| `CleanSheet/ui/popups/popup_sheet_selector.py:176` | UI copy | Transaction | Transaction |  |
| `CleanSheet/ui/popups/popup_sheet_selector.py:181` | UI copy | Dimension | Dimension |  |
| `CleanSheet/ui/popups/popup_sheet_selector.py:191` | UI copy | Row | Row |  |
| `CleanSheet/ui/popups/popup_sheet_selector.py:319` | UI copy | Cancel | Cancel |  |
| `CleanSheet/ui/popups/popup_sheet_selector.py:326` | UI copy | Confirm Selection | Confirm Selection |  |

## `CleanSheet/ui/popups/popup_single_sheet.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/popups/popup_single_sheet.py:112` | UI copy | <br> | <br> |  |
| `CleanSheet/ui/popups/popup_single_sheet.py:139` | UI copy | SHEET | SHEET |  |
| `CleanSheet/ui/popups/popup_single_sheet.py:169` | UI copy | HEADER ROW | Header Row | Avoid all-caps headings. |
| `CleanSheet/ui/popups/popup_single_sheet.py:225` | UI copy | Cancel | Cancel |  |
| `CleanSheet/ui/popups/popup_single_sheet.py:236` | UI copy | Select Sheet | Select Sheet |  |
| `CleanSheet/ui/popups/popup_single_sheet.py:250` | UI copy | No sheets available in this file. | No sheets available in this file. |  |
| `CleanSheet/ui/popups/popup_single_sheet.py:254` | UI copy | Select a sheet. | Select a sheet. |  |

## `CleanSheet/ui/screen0_launcher.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/screen0_launcher.py:178` | UI copy | All Projects | All Projects |  |
| `CleanSheet/ui/screen0_launcher.py:184` | UI copy | 0 projects | 0 projects |  |
| `CleanSheet/ui/screen0_launcher.py:205` | UI copy | Search projects… | Search projects… |  |
| `CleanSheet/ui/screen0_launcher.py:237` | UI copy | + New Project | + New Project |  |
| `CleanSheet/ui/screen0_launcher.py:297` | UI copy | CS | CS |  |
| `CleanSheet/ui/screen0_launcher.py:303` | UI copy | CS | CS |  |
| `CleanSheet/ui/screen0_launcher.py:323` | UI copy | Data Cleansing and Standardization Tool. | Data Cleansing and Standardization Tool. |  |
| `CleanSheet/ui/screen0_launcher.py:339` | UI copy | SELECTED PROJECT | Selected Project | Avoid all-caps headings. |
| `CleanSheet/ui/screen0_launcher.py:396` | UI copy | Open Project | Open Project |  |
| `CleanSheet/ui/screen0_launcher.py:404` | UI copy | Delete | Delete |  |
| `CleanSheet/ui/screen0_launcher.py:429` | UI copy | {theme.company_name()} v1.0 · 0 projects loaded | {theme.company_name()} v1.0 · 0 projects loaded |  |
| `CleanSheet/ui/screen0_launcher.py:435` | UI copy | Dark Mode | Dark Mode |  |
| `CleanSheet/ui/screen0_launcher.py:477` | UI copy | {count} project{'s' if count != 1 else ''} | {count} project{'s' if count != 1 else ''} |  |
| `CleanSheet/ui/screen0_launcher.py:479` | UI copy | {theme.company_name()} v1.0 · {count} project{'s' if count != 1 else ''} loaded | {theme.company_name()} v1.0 · {count} project{'s' if count != 1 else ''} loaded |  |
| `CleanSheet/ui/screen0_launcher.py:482` | UI copy | No projects yet. | No projects yet. |  |
| `CleanSheet/ui/screen0_launcher.py:629` | UI copy | Navigation Error | Navigation Error |  |
| `CleanSheet/ui/screen0_launcher.py:632` | Dialog | Title: Error<br>Body: Could not open project:<br>{exc} | Title: Couldn't open project<br>Body: We couldn't open project.<br><br>Details: {exc}<br><br>Make sure the file exists, is a supported Excel file, and isn't open in Excel, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/screen0_launcher.py:645` | UI copy | Confirm Delete | Confirm Delete |  |
| `CleanSheet/ui/screen0_launcher.py:646` | UI copy | Delete project '{project_path.name}'?<br><br> | Delete project '{project_path.name}'?<br><br> |  |
| `CleanSheet/ui/screen0_launcher.py:658` | Dialog | Title: Error<br>Body: Could not delete project:<br>{exc} | Title: Couldn't delete project<br>Body: We couldn't delete project.<br><br>Details: {exc}<br><br>Make sure the item isn't in use, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/screen0_launcher.py:729` | UI copy | <br> | <br> |  |
| `CleanSheet/ui/screen0_launcher.py:774` | UI copy | e.g. Sales Module | e.g. Sales Module |  |
| `CleanSheet/ui/screen0_launcher.py:779` | UI copy | e.g. Acme Corp | e.g. Acme Corp |  |
| `CleanSheet/ui/screen0_launcher.py:789` | UI copy | SAVE LOCATION | Save Location | Avoid all-caps headings. |
| `CleanSheet/ui/screen0_launcher.py:798` | UI copy | Choose a folder… | Choose a folder… |  |
| `CleanSheet/ui/screen0_launcher.py:803` | UI copy | Browse… | Browse… |  |
| `CleanSheet/ui/screen0_launcher.py:832` | UI copy | Cancel | Cancel |  |
| `CleanSheet/ui/screen0_launcher.py:839` | UI copy | Create Project | Create Project |  |
| `CleanSheet/ui/screen0_launcher.py:870` | UI copy | Company name is required. | Company name is required. |  |
| `CleanSheet/ui/screen0_launcher.py:873` | UI copy | Please choose a save location. | Please choose a save location. |  |
| `CleanSheet/ui/screen0_launcher.py:876` | UI copy | Save location does not exist. | Save location does not exist. |  |
| `CleanSheet/ui/screen0_launcher.py:896` | UI copy | Could not create project: {exc} | We couldn't create project: {exc} | Use plain language; label technical details. |

## `CleanSheet/ui/screen15_chain_mapper.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/screen15_chain_mapper.py:194` | UI copy | {theme.company_name()}</span> | {theme.company_name()}</span> |  |
| `CleanSheet/ui/screen15_chain_mapper.py:195` | UI copy | <br> | <br> |  |
| `CleanSheet/ui/screen15_chain_mapper.py:203` | UI copy | SETUP PROGRESS | Setup Progress | Avoid all-caps headings. |
| `CleanSheet/ui/screen15_chain_mapper.py:226` | UI copy | PROJECT | PROJECT |  |
| `CleanSheet/ui/screen15_chain_mapper.py:331` | UI copy | <br> | <br> |  |
| `CleanSheet/ui/screen15_chain_mapper.py:360` | UI copy | Loading columns… | Loading columns… |  |
| `CleanSheet/ui/screen15_chain_mapper.py:379` | UI copy | RULES | RULES |  |
| `CleanSheet/ui/screen15_chain_mapper.py:390` | UI copy | • {rule} | • {rule} |  |
| `CleanSheet/ui/screen15_chain_mapper.py:417` | UI copy | Cancel | Cancel |  |
| `CleanSheet/ui/screen15_chain_mapper.py:423` | UI copy | Confirm Chain → | Confirm Chain → |  |
| `CleanSheet/ui/screen15_chain_mapper.py:451` | UI copy | Primary sheet has no columns — cannot chain. | Primary sheet has no columns — cannot chain. |  |
| `CleanSheet/ui/screen15_chain_mapper.py:457` | UI copy | Error loading columns: {exc} | Error loading columns: {exc} |  |
| `CleanSheet/ui/screen15_chain_mapper.py:534` | UI copy | primaryColLocked | primaryColLocked |  |
| `CleanSheet/ui/screen15_chain_mapper.py:626` | UI copy | Duplicate mapping — each secondary column can only be used once. | Duplicate mapping — each secondary column can only be used once. |  |
| `CleanSheet/ui/screen15_chain_mapper.py:664` | UI copy | EXTRA/UNMAPPED COLUMNS — not mapped with any primary file column | EXTRA/UNMAPPED COLUMNS — not mapped with any primary file column |  |
| `CleanSheet/ui/screen15_chain_mapper.py:829` | UI copy | Save failed: {exc} | Save failed: {exc} |  |

## `CleanSheet/ui/screen1_sources.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/screen1_sources.py:136` | UI copy | <br> | <br> |  |
| `CleanSheet/ui/screen1_sources.py:145` | UI copy | SETUP PROGRESS | Setup Progress | Avoid all-caps headings. |
| `CleanSheet/ui/screen1_sources.py:169` | UI copy | PROJECT | PROJECT |  |
| `CleanSheet/ui/screen1_sources.py:218` | UI copy | ✕ Cancel | ✕ Cancel | Trim extra whitespace. |
| `CleanSheet/ui/screen1_sources.py:227` | UI copy | ← Back to Projects | ← Back To Projects | Button labels in title case. |
| `CleanSheet/ui/screen1_sources.py:256` | UI copy | + Add File | + Add File |  |
| `CleanSheet/ui/screen1_sources.py:284` | UI copy | Add at least one Transaction and one Dimension file to continue. | Add at least one Transaction and one Dimension file to continue. |  |
| `CleanSheet/ui/screen1_sources.py:313` | UI copy | LOADED FILES | Loaded Files | Avoid all-caps headings. |
| `CleanSheet/ui/screen1_sources.py:320` | UI copy | 0 files | 0 files |  |
| `CleanSheet/ui/screen1_sources.py:350` | UI copy | Both Transaction and Dimension sheets must be present to continue | Both Transaction and Dimension sheets must be present to continue |  |
| `CleanSheet/ui/screen1_sources.py:357` | UI copy | Confirm → | Confirm → |  |
| `CleanSheet/ui/screen1_sources.py:439` | UI copy | {existing_count + new_count} file{'s' if (existing_count + new_count) != 1 else ''} | {existing_count + new_count} file{'s' if (existing_count + new_count) != 1 else ''} |  |
| `CleanSheet/ui/screen1_sources.py:492` | UI copy | No files added yet | No files added yet |  |
| `CleanSheet/ui/screen1_sources.py:498` | UI copy | Click Add File to add an Excel file here | Click Add File to add an Excel file here |  |
| `CleanSheet/ui/screen1_sources.py:536` | UI copy | Previously loaded tables | Previously loaded tables |  |
| `CleanSheet/ui/screen1_sources.py:547` | UI copy | {t} · T | {t} · T |  |
| `CleanSheet/ui/screen1_sources.py:555` | UI copy | {t} · D | {t} · D |  |
| `CleanSheet/ui/screen1_sources.py:566` | UI copy | Saved | Saved |  |
| `CleanSheet/ui/screen1_sources.py:611` | UI copy | Remove | Remove |  |
| `CleanSheet/ui/screen1_sources.py:706` | UI copy | Transaction | Transaction |  |
| `CleanSheet/ui/screen1_sources.py:746` | UI copy | Both Transaction and Dimension sheets must be present to continue | Both Transaction and Dimension sheets must be present to continue |  |
| `CleanSheet/ui/screen1_sources.py:789` | Dialog | Title: Error<br>Body: Could not read Excel file:<br>{exc} | Title: Couldn't read Excel file<br>Body: We couldn't read Excel file.<br><br>Details: {exc}<br><br>Make sure the file exists, is a supported Excel file, and isn't open in Excel, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/screen1_sources.py:862` | Dialog | Title: Error<br>Body: Could not read Excel file:<br>{exc} | Title: Couldn't read Excel file<br>Body: We couldn't read Excel file.<br><br>Details: {exc}<br><br>Make sure the file exists, is a supported Excel file, and isn't open in Excel, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/screen1_sources.py:889` | UI copy | Remove Chain Link | Remove Chain Link |  |
| `CleanSheet/ui/screen1_sources.py:890` | UI copy | Remove '{entry['sheet_name']}' from the chain? | Remove '{entry['sheet_name']}' from the chain? |  |
| `CleanSheet/ui/screen1_sources.py:920` | UI copy | Delete Sheet | Delete Sheet |  |
| `CleanSheet/ui/screen1_sources.py:921` | UI copy | Remove '{sheet['sheet_name']}' from the project?<br><br> | Remove '{sheet['sheet_name']}' from the project?<br><br> |  |
| `CleanSheet/ui/screen1_sources.py:962` | UI copy | Continue to Mapper? | Continue to Mapper? |  |
| `CleanSheet/ui/screen1_sources.py:963` | UI copy | Are you sure you want to proceed?<br><br> | Are you sure you want to proceed?<br><br> |  |
| `CleanSheet/ui/screen1_sources.py:994` | UI copy | Data Import Warnings | Data Import Warnings |  |
| `CleanSheet/ui/screen1_sources.py:995` | UI copy | <br><br> | <br><br> |  |
| `CleanSheet/ui/screen1_sources.py:1002` | UI copy | Screen 2 | Screen 2 |  |
| `CleanSheet/ui/screen1_sources.py:1002` | UI copy | Data sources saved. Screen 2 is not built yet. | Data sources saved. Screen 2 is not built yet. |  |
| `CleanSheet/ui/screen1_sources.py:1007` | Dialog | Title: Error<br>Body: Could not save selected sheets:<br>{exc} | Title: Couldn't save selected sheets<br>Body: We couldn't save selected sheets.<br><br>Details: {exc}<br><br>Check the destination folder is writable and the output file isn't open, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |

## `CleanSheet/ui/screen2_mappings.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/screen2_mappings.py:156` | UI copy | <br> | <br> |  |
| `CleanSheet/ui/screen2_mappings.py:165` | UI copy | SETUP PROGRESS | Setup Progress | Avoid all-caps headings. |
| `CleanSheet/ui/screen2_mappings.py:185` | UI copy | PROJECT | PROJECT |  |
| `CleanSheet/ui/screen2_mappings.py:231` | UI copy | ✕ Cancel | ✕ Cancel | Trim extra whitespace. |
| `CleanSheet/ui/screen2_mappings.py:241` | UI copy | ← Back to Data Loader | ← Back To Data Loader | Button labels in title case. |
| `CleanSheet/ui/screen2_mappings.py:348` | UI copy | <br> | <br> |  |
| `CleanSheet/ui/screen2_mappings.py:433` | UI copy | \u2190\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2192 | \u2190\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2192 |  |
| `CleanSheet/ui/screen2_mappings.py:445` | UI copy | Confirm Mapping | Confirm Mapping |  |
| `CleanSheet/ui/screen2_mappings.py:488` | UI copy | CONFIRMED MAPPINGS | Confirmed Mappings | Avoid all-caps headings. |
| `CleanSheet/ui/screen2_mappings.py:493` | UI copy | 0 mappings | 0 mappings |  |
| `CleanSheet/ui/screen2_mappings.py:553` | UI copy | {count} table{'s' if count != 1 else ''} | {count} table{'s' if count != 1 else ''} |  |
| `CleanSheet/ui/screen2_mappings.py:622` | UI copy | Finish Setup → | Finish Setup → |  |
| `CleanSheet/ui/screen2_mappings.py:656` | UI copy | Add new mappings above, then click Finish to save and continue. | Add new mappings above, then click Finish to save and continue. |  |
| `CleanSheet/ui/screen2_mappings.py:658` | UI copy | At least 1 mapping confirmed. Click Finish when ready. | At least 1 mapping confirmed. Click Finish when ready. |  |
| `CleanSheet/ui/screen2_mappings.py:666` | UI copy | Add at least 1 mapping before finishing setup. | Add at least 1 mapping before finishing setup. |  |
| `CleanSheet/ui/screen2_mappings.py:711` | UI copy | Remove '{table_name}' from this project | Remove '{table_name}' from this project |  |
| `CleanSheet/ui/screen2_mappings.py:754` | UI copy | Remove Table | Remove Table |  |
| `CleanSheet/ui/screen2_mappings.py:755` | UI copy | Remove '{table_name}' from this project?<br><br> | Remove '{table_name}' from this project?<br><br> |  |
| `CleanSheet/ui/screen2_mappings.py:790` | Dialog | Title: Error<br>Body: Could not remove '{table_name}':<br>{exc} | Title: Couldn't remove '{table_name}'<br>Body: We couldn't remove '{table_name}'.<br><br>Details: {exc}<br><br>Make sure the item isn't in use, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/screen2_mappings.py:845` | Dialog | Title: Error<br>Body: Could not load dim table '{table_name}':<br>{exc} | Title: Couldn't load dim table '{table_name}'<br>Body: We couldn't load dim table '{table_name}'.<br><br>Details: {exc}<br><br>Make sure the file exists, is a supported Excel file, and isn't open in Excel, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/screen2_mappings.py:870` | Dialog | Title: Error<br>Body: Could not load transaction table '{table_name}':<br>{exc} | Title: Couldn't load transaction table '{table_name}'<br>Body: We couldn't load transaction table '{table_name}'.<br><br>Details: {exc}<br><br>Make sure the file exists, is a supported Excel file, and isn't open in Excel, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/screen2_mappings.py:1037` | UI copy | Low Column Match | Low Column Match |  |
| `CleanSheet/ui/screen2_mappings.py:1040` | UI copy | Map Anyway | Map Anyway |  |
| `CleanSheet/ui/screen2_mappings.py:1041` | UI copy | Change Column | Change Column |  |
| `CleanSheet/ui/screen2_mappings.py:1062` | UI copy | {total} mapping{'s' if total != 1 else ''} | {total} mapping{'s' if total != 1 else ''} |  |
| `CleanSheet/ui/screen2_mappings.py:1070` | UI copy | No mappings added yet. | No mappings added yet. |  |
| `CleanSheet/ui/screen2_mappings.py:1147` | UI copy | Existing mapping — manage from the main workspace | Existing mapping — manage from the main workspace |  |
| `CleanSheet/ui/screen2_mappings.py:1197` | Dialog | Title: Done<br>Body: Mappings saved. Screen 3 not built yet. | Title: Done<br>Body: Mappings saved. Screen 3 not built yet. |  |
| `CleanSheet/ui/screen2_mappings.py:1200` | Dialog | Title: Error<br>Body: Could not save mappings:<br>{exc} | Title: Couldn't save mappings<br>Body: We couldn't save mappings.<br><br>Details: {exc}<br><br>Check the destination folder is writable and the output file isn't open, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/screen2_mappings.py:1211` | UI copy | Finish Setup | Finish Setup |  |
| `CleanSheet/ui/screen2_mappings.py:1212` | UI copy | All tables are mapped.<br><br>Do you want to finish setup and continue? | All tables are mapped.<br><br>Do you want to finish setup and continue? |  |
| `CleanSheet/ui/screen2_mappings.py:1214` | UI copy | Finish Setup | Finish Setup |  |
| `CleanSheet/ui/screen2_mappings.py:1215` | UI copy | Go Back | Go Back |  |
| `CleanSheet/ui/screen2_mappings.py:1232` | UI copy | Unmapped Tables | Unmapped Tables |  |
| `CleanSheet/ui/screen2_mappings.py:1234` | UI copy | The following tables have no mappings and will be passed through unchanged:<br><br> | The following tables have no mappings and will be passed through unchanged:<br><br> |  |
| `CleanSheet/ui/screen2_mappings.py:1235` | UI copy | {unmapped_str}<br><br>Do you want to continue? | {unmapped_str}<br><br>Do you want to continue? |  |
| `CleanSheet/ui/screen2_mappings.py:1238` | UI copy | Continue | Continue |  |
| `CleanSheet/ui/screen2_mappings.py:1239` | UI copy | Go Back | Go Back |  |
| `CleanSheet/ui/screen2_mappings.py:1246` | Dialog | Title: Error<br>Body: Could not read existing mappings:<br>{exc} | Title: Couldn't read existing mappings<br>Body: We couldn't read existing mappings.<br><br>Details: {exc}<br><br>Make sure the file exists, is a supported Excel file, and isn't open in Excel, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |

## `CleanSheet/ui/screen3_main.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/screen3_main.py:62` | UI copy | Delete Mapping | Delete Mapping |  |
| `CleanSheet/ui/screen3_main.py:84` | UI copy | Delete Mapping | Delete Mapping |  |
| `CleanSheet/ui/screen3_main.py:110` | UI copy | This mapping will be permanently removed. If this was the only mapping | This mapping will be permanently removed. If this was the only mapping | Trim extra whitespace. |
| `CleanSheet/ui/screen3_main.py:111` | UI copy | referencing the dimension table, it will become orphaned and eligible for deletion. | referencing the dimension table, it will become orphaned and eligible for deletion. |  |
| `CleanSheet/ui/screen3_main.py:129` | UI copy | Cancel | Cancel |  |
| `CleanSheet/ui/screen3_main.py:140` | UI copy | Delete Mapping | Delete Mapping |  |
| `CleanSheet/ui/screen3_main.py:206` | Dialog | Title: Error<br>Body: Could not load mappings:<br>{exc} | Title: Couldn't load mappings<br>Body: We couldn't load mappings.<br><br>Details: {exc}<br><br>Make sure the file exists, is a supported Excel file, and isn't open in Excel, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/screen3_main.py:330` | UI copy | {theme.company_name()}</span> | {theme.company_name()}</span> |  |
| `CleanSheet/ui/screen3_main.py:331` | UI copy | <br> | <br> |  |
| `CleanSheet/ui/screen3_main.py:349` | UI copy | WORKSPACE | Workspace | Avoid all-caps headings. |
| `CleanSheet/ui/screen3_main.py:356` | UI copy | Project | Project |  |
| `CleanSheet/ui/screen3_main.py:375` | UI copy | ← Back to Launcher | ← Back To Launcher | Button labels in title case. |
| `CleanSheet/ui/screen3_main.py:410` | UI copy | MAPPINGS | Mappings | Avoid all-caps headings. |
| `CleanSheet/ui/screen3_main.py:420` | UI copy | Add new mapping | Add new mapping |  |
| `CleanSheet/ui/screen3_main.py:670` | UI copy | Dimension Table Now Orphaned | Dimension Table Now Orphaned |  |
| `CleanSheet/ui/screen3_main.py:671` | UI copy | The dimension table <b>{dim_table}</b> is no longer referenced | The dimension table <b>{dim_table}</b> is no longer referenced | Trim extra whitespace. |
| `CleanSheet/ui/screen3_main.py:690` | UI copy | Error | Error |  |
| `CleanSheet/ui/screen3_main.py:690` | UI copy | Could not delete mapping:<br>{exc} | We couldn't delete mapping.<br><br>Details: {exc} | Use plain language; label technical details. |
| `CleanSheet/ui/screen3_main.py:784` | Dialog | Title: Error<br>Body: Could not refresh project:<br>{exc} | Title: Couldn't refresh project<br>Body: We couldn't refresh project.<br><br>Details: {exc}<br><br>Try reopening the project. If it keeps happening, open the log folder and share the error details. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/screen3_main.py:793` | Dialog | Title: Error<br>Body: Could not refresh project:<br>{exc} | Title: Couldn't refresh project<br>Body: We couldn't refresh project.<br><br>Details: {exc}<br><br>Try reopening the project. If it keeps happening, open the log folder and share the error details. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/screen3_main.py:802` | Dialog | Title: Error<br>Body: Could not refresh project:<br>{exc} | Title: Couldn't refresh project<br>Body: We couldn't refresh project.<br><br>Details: {exc}<br><br>Try reopening the project. If it keeps happening, open the log folder and share the error details. | Make the title specific. Use plain language; label technical details. Add a next step. |

## `CleanSheet/ui/views/view_d_sources.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/views/view_d_sources.py:60` | UI copy | Delete Orphaned Dimension Table | Delete Orphaned Dimension Table |  |
| `CleanSheet/ui/views/view_d_sources.py:76` | UI copy | Delete Dimension Table | Delete Dimension Table |  |
| `CleanSheet/ui/views/view_d_sources.py:92` | UI copy | and is eligible for deletion.<br><br> | and is eligible for deletion.<br><br> |  |
| `CleanSheet/ui/views/view_d_sources.py:93` | UI copy | This will <b>permanently remove</b> the dimension table and all its data. | This will <b>permanently remove</b> the dimension table and all its data. | Trim extra whitespace. |
| `CleanSheet/ui/views/view_d_sources.py:112` | UI copy | Cancel | Cancel |  |
| `CleanSheet/ui/views/view_d_sources.py:123` | UI copy | Delete Permanently | Delete Permanently |  |
| `CleanSheet/ui/views/view_d_sources.py:185` | UI copy | Dimension Tables | Dimension Tables |  |
| `CleanSheet/ui/views/view_d_sources.py:191` | UI copy | Add new dimension tables here. Orphaned tables (no active mappings) | Add dimension tables here. Tables with no active mappings | Trim extra whitespace. Rewrite for clarity. |
| `CleanSheet/ui/views/view_d_sources.py:192` | UI copy | may be permanently deleted. | can be deleted. | Rewrite for clarity. |
| `CleanSheet/ui/views/view_d_sources.py:230` | UI copy | CURRENT DIMENSION TABLES | Current Dimension Tables | Avoid all-caps headings. |
| `CleanSheet/ui/views/view_d_sources.py:256` | UI copy | Search dimension tables... | Search dimension tables... |  |
| `CleanSheet/ui/views/view_d_sources.py:388` | UI copy | View | View |  |
| `CleanSheet/ui/views/view_d_sources.py:400` | UI copy | Delete | Delete |  |
| `CleanSheet/ui/views/view_d_sources.py:411` | UI copy | Locked | Locked |  |
| `CleanSheet/ui/views/view_d_sources.py:460` | UI copy | Chained dimension · {len(chain)} source{'s' if len(chain) != 1 else ''} | Chained dimension · {len(chain)} source{'s' if len(chain) != 1 else ''} |  |
| `CleanSheet/ui/views/view_d_sources.py:473` | UI copy | Delete | Delete |  |
| `CleanSheet/ui/views/view_d_sources.py:568` | Dialog | Title: Error<br>Body: Could not read file:<br>{exc} | Title: Couldn't read file<br>Body: We couldn't read file.<br><br>Details: {exc}<br><br>Make sure the file exists, is a supported Excel file, and isn't open in Excel, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/views/view_d_sources.py:583` | UI copy | Delete Chained Source | Delete Chained Source |  |
| `CleanSheet/ui/views/view_d_sources.py:584` | UI copy | This will permanently remove the chained dimension '{dim_name}' | This will permanently remove the chained dimension '{dim_name}' | Trim extra whitespace. |
| `CleanSheet/ui/views/view_d_sources.py:616` | Dialog | Title: Error<br>Body: Could not delete source:<br>{exc} | Title: Couldn't delete source<br>Body: We couldn't delete source.<br><br>Details: {exc}<br><br>Make sure the item isn't in use, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/views/view_d_sources.py:636` | Dialog | Title: Error<br>Body: Could not load table:<br>{exc} | Title: Couldn't load table<br>Body: We couldn't load table.<br><br>Details: {exc}<br><br>Make sure the file exists, is a supported Excel file, and isn't open in Excel, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/views/view_d_sources.py:666` | UI copy | Error | Error |  |
| `CleanSheet/ui/views/view_d_sources.py:666` | UI copy | Could not delete dimension table:<br>{exc} | We couldn't delete dimension table.<br><br>Details: {exc} | Use plain language; label technical details. |

## `CleanSheet/ui/views/view_history.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/views/view_history.py:74` | UI copy | Take Snapshot | Take Snapshot |  |
| `CleanSheet/ui/views/view_history.py:89` | UI copy | Take Snapshot | Take Snapshot |  |
| `CleanSheet/ui/views/view_history.py:103` | UI copy | Enter a description for this snapshot: | Enter a description for this snapshot: |  |
| `CleanSheet/ui/views/view_history.py:110` | UI copy | e.g. Before Q2 mapping review | e.g. Before Q2 mapping review |  |
| `CleanSheet/ui/views/view_history.py:136` | UI copy | Cancel | Cancel |  |
| `CleanSheet/ui/views/view_history.py:147` | UI copy | Create Snapshot | Create Snapshot |  |
| `CleanSheet/ui/views/view_history.py:161` | UI copy | Description is required. | Description is required. |  |
| `CleanSheet/ui/views/view_history.py:200` | UI copy | Commit History | Commit History |  |
| `CleanSheet/ui/views/view_history.py:206` | UI copy | Select a commit to inspect its details, edit the label, or revert — | Select a snapshot to review, rename, or revert — | Trim extra whitespace. Rewrite for clarity. |
| `CleanSheet/ui/views/view_history.py:207` | UI copy | reverting restores transactions, dimension tables, and mappings together. | Reverting restores transactions, dimension tables, and mappings to that snapshot. | Rewrite for clarity. |
| `CleanSheet/ui/views/view_history.py:216` | UI copy | + Take Snapshot | + Take Snapshot |  |
| `CleanSheet/ui/views/view_history.py:258` | UI copy | COMMITS | COMMITS |  |
| `CleanSheet/ui/views/view_history.py:298` | UI copy | COMMIT DETAILS | Commit Details | Avoid all-caps headings. |
| `CleanSheet/ui/views/view_history.py:324` | UI copy | Select a commit | Select a commit |  |
| `CleanSheet/ui/views/view_history.py:362` | UI copy | Edit label… | Edit label… |  |
| `CleanSheet/ui/views/view_history.py:427` | Dialog | Title: Error<br>Body: Could not create snapshot:<br>{exc} | Title: Couldn't create snapshot<br>Body: We couldn't create snapshot.<br><br>Details: {exc}<br><br>Try again. If it keeps happening, check the log for more details. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/views/view_history.py:441` | UI copy | Select a commit | Select a commit |  |
| `CleanSheet/ui/views/view_history.py:451` | UI copy | History is OFF in settings. | History is OFF in settings. |  |
| `CleanSheet/ui/views/view_history.py:473` | UI copy | HEAD → {display} | HEAD → {display} | Trim extra whitespace. |
| `CleanSheet/ui/views/view_history.py:482` | UI copy | No commits yet. | No commits yet. |  |
| `CleanSheet/ui/views/view_history.py:513` | UI copy | {display_id} · {created} | {display_id} · {created} | Trim extra whitespace. |
| `CleanSheet/ui/views/view_history.py:521` | UI copy | HEAD | HEAD |  |
| `CleanSheet/ui/views/view_history.py:642` | UI copy | Already at this commit. | Already at this commit. |  |
| `CleanSheet/ui/views/view_history.py:677` | UI copy | Reverted | Reverted |  |
| `CleanSheet/ui/views/view_history.py:678` | UI copy | Reverted to {display_id}.<br> | Reverted to {display_id}.<br> |  |
| `CleanSheet/ui/views/view_history.py:679` | UI copy | Transactions, dimension tables, and mappings have been restored. | Transactions, dimension tables, and mappings have been restored. |  |
| `CleanSheet/ui/views/view_history.py:684` | UI copy | Error | Error |  |
| `CleanSheet/ui/views/view_history.py:684` | UI copy | Could not revert:<br>{exc} | We couldn't revert.<br><br>Details: {exc} | Use plain language; label technical details. |

## `CleanSheet/ui/views/view_mapping.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/views/view_mapping.py:295` | UI copy | {tx_t}.{tx_c} | {tx_t}.{tx_c} |  |
| `CleanSheet/ui/views/view_mapping.py:296` | UI copy | </span> | </span> |  |
| `CleanSheet/ui/views/view_mapping.py:325` | UI copy | row 0–0 of 0 | row 0–0 of 0 |  |
| `CleanSheet/ui/views/view_mapping.py:331` | UI copy | Prev | Prev |  |
| `CleanSheet/ui/views/view_mapping.py:338` | UI copy | Next | Next |  |
| `CleanSheet/ui/views/view_mapping.py:347` | UI copy | ↻ Refresh | ↻ Refresh | Trim extra whitespace. |
| `CleanSheet/ui/views/view_mapping.py:397` | UI copy | TABLES | TABLES |  |
| `CleanSheet/ui/views/view_mapping.py:405` | UI copy | Error rows highlighted · Click error to select | Error rows highlighted · Click error to select | Trim extra whitespace. |
| `CleanSheet/ui/views/view_mapping.py:479` | UI copy | No errors found | No errors found |  |
| `CleanSheet/ui/views/view_mapping.py:487` | UI copy | All values match the dimension table | All values match the dimension table |  |
| `CleanSheet/ui/views/view_mapping.py:515` | UI copy | ⚠ ERRORS | ⚠ ERRORS | Trim extra whitespace. |
| `CleanSheet/ui/views/view_mapping.py:523` | UI copy | 0 unresolved | 0 unresolved |  |
| `CleanSheet/ui/views/view_mapping.py:557` | UI copy | Select an error below to resolve it. | Select an error below to resolve it. |  |
| `CleanSheet/ui/views/view_mapping.py:564` | UI copy | Generate Output → | Generate Output → | Trim extra whitespace. |
| `CleanSheet/ui/views/view_mapping.py:579` | UI copy | Generate Output | Generate Output |  |
| `CleanSheet/ui/views/view_mapping.py:594` | UI copy | Replace Value | Replace Value |  |
| `CleanSheet/ui/views/view_mapping.py:613` | UI copy | Add to Dimension | Add To Dimension | Button labels in title case. |
| `CleanSheet/ui/views/view_mapping.py:726` | UI copy | row 0–0 of 0 | row 0–0 of 0 |  |
| `CleanSheet/ui/views/view_mapping.py:760` | UI copy | row {start + 1}–{end} of {total_rows} | row {start + 1}–{end} of {total_rows} |  |
| `CleanSheet/ui/views/view_mapping.py:788` | UI copy | Loading… | Loading… |  |
| `CleanSheet/ui/views/view_mapping.py:822` | UI copy | {visible_total:,} errors | {visible_total:,} errors |  |
| `CleanSheet/ui/views/view_mapping.py:824` | UI copy | {visible_total:,} unresolved | {visible_total:,} unresolved |  |
| `CleanSheet/ui/views/view_mapping.py:838` | UI copy | {overflow:,} more errors not shown — | {overflow:,} more errors not shown — | Trim extra whitespace. |
| `CleanSheet/ui/views/view_mapping.py:839` | UI copy | resolve the ones above then click ↻ Refresh. | resolve the ones above then click ↻ Refresh. |  |
| `CleanSheet/ui/views/view_mapping.py:850` | UI copy | Showing first {len(self._errors):,} of {self._total_errors:,} errors. | Showing first {len(self._errors):,} of {self._total_errors:,} errors. | Trim extra whitespace. |
| `CleanSheet/ui/views/view_mapping.py:851` | UI copy | Fix these, then refresh to see more. | Fix these, then refresh to see more. |  |
| `CleanSheet/ui/views/view_mapping.py:878` | UI copy | Row {row_num} | Row {row_num} |  |
| `CleanSheet/ui/views/view_mapping.py:899` | UI copy | (empty) | (empty) |  |
| `CleanSheet/ui/views/view_mapping.py:907` | UI copy | Not in dimension | Not in dimension |  |
| `CleanSheet/ui/views/view_mapping.py:918` | UI copy | Ignore | Ignore |  |
| `CleanSheet/ui/views/view_mapping.py:935` | UI copy | Delete | Delete |  |
| `CleanSheet/ui/views/view_mapping.py:1148` | UI copy | Error | Error |  |
| `CleanSheet/ui/views/view_mapping.py:1148` | UI copy | Could not replace:<br>{exc} | We couldn't replace.<br><br>Details: {exc} | Use plain language; label technical details. |
| `CleanSheet/ui/views/view_mapping.py:1211` | UI copy | Error | Error |  |
| `CleanSheet/ui/views/view_mapping.py:1211` | UI copy | Could not add row:<br>{exc} | We couldn't add row.<br><br>Details: {exc} | Use plain language; label technical details. |
| `CleanSheet/ui/views/view_mapping.py:1371` | Dialog | Title: Error<br>Body: Could not delete row:<br>{exc} | Title: Couldn't delete row<br>Body: We couldn't delete row.<br><br>Details: {exc}<br><br>Make sure the item isn't in use, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/views/view_mapping.py:1405` | UI copy | Export Complete | Export Complete |  |
| `CleanSheet/ui/views/view_mapping.py:1406` | UI copy | Final file created:<br>{path}<br><br>Open the output folder? | Final file created:<br>{path}<br><br>Open the output folder? |  |
| `CleanSheet/ui/views/view_mapping.py:1413` | UI copy | explorer "{folder}" | explorer "{folder}" |  |
| `CleanSheet/ui/views/view_mapping.py:1417` | Dialog | Title: Export Failed<br>Body: Could not generate final file:<br>{exc} | Title: Couldn't generate final file<br>Body: We couldn't generate final file.<br><br>Details: {exc}<br><br>Check the destination folder is writable and the output file isn't open, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/views/view_mapping.py:1573` | UI copy | Cancel | Cancel |  |
| `CleanSheet/ui/views/view_mapping.py:1576` | UI copy | QPushButton { | QPushButton { | Trim extra whitespace. |
| `CleanSheet/ui/views/view_mapping.py:1591` | UI copy | QPushButton {{ | QPushButton {{ | Trim extra whitespace. |
| `CleanSheet/ui/views/view_mapping.py:1624` | UI copy | Multiple Occurrences Found | Multiple Occurrences Found |  |
| `CleanSheet/ui/views/view_mapping.py:1641` | UI copy | Multiple Occurrences Found | Multiple Occurrences Found |  |
| `CleanSheet/ui/views/view_mapping.py:1652` | UI copy | The value "{display}" appears on {count_label} rows in this mapping.<br><br> | The value "{display}" appears on {count_label} rows in this mapping.<br><br> |  |
| `CleanSheet/ui/views/view_mapping.py:1653` | UI copy | {verb} all matching rows, or only Row {selected_row}? | {verb} all matching rows, or only Row {selected_row}? |  |
| `CleanSheet/ui/views/view_mapping.py:1670` | UI copy | Cancel | Cancel |  |
| `CleanSheet/ui/views/view_mapping.py:1673` | UI copy | QPushButton { | QPushButton { | Trim extra whitespace. |
| `CleanSheet/ui/views/view_mapping.py:1685` | UI copy | Just Row {selected_row} | Just Row {selected_row} |  |
| `CleanSheet/ui/views/view_mapping.py:1691` | UI copy | {verb} All ({count_label} rows) | {verb} All ({count_label} rows) | Trim extra whitespace. |

## `CleanSheet/ui/views/view_settings.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/views/view_settings.py:92` | UI copy | Settings | Settings |  |
| `CleanSheet/ui/views/view_settings.py:98` | UI copy | Update project details and history preference, then save to apply changes. | Update project details and history settings, then save. | Rewrite for clarity. |
| `CleanSheet/ui/views/view_settings.py:173` | UI copy | Enable History | Enable History |  |
| `CleanSheet/ui/views/view_settings.py:178` | UI copy | When enabled, a snapshot is created after each table update or revert. | When enabled, a snapshot is created after each table update or revert. |  |
| `CleanSheet/ui/views/view_settings.py:215` | UI copy | Open Folder | Open Folder |  |
| `CleanSheet/ui/views/view_settings.py:253` | UI copy | About | About |  |
| `CleanSheet/ui/views/view_settings.py:264` | UI copy | Save Changes | Save Changes |  |
| `CleanSheet/ui/views/view_settings.py:305` | UI copy | History Off Warning | History Off Warning |  |
| `CleanSheet/ui/views/view_settings.py:306` | UI copy | Existing history will be kept but no new snapshots will be created. Continue? | Existing history will be kept but no new snapshots will be created. Continue? |  |
| `CleanSheet/ui/views/view_settings.py:324` | Dialog | Title: Saved<br>Body: Settings saved successfully. | Title: Saved<br>Body: Settings saved successfully. |  |
| `CleanSheet/ui/views/view_settings.py:329` | UI copy | Error | Error |  |
| `CleanSheet/ui/views/view_settings.py:329` | UI copy | Could not save settings:<br>{exc} | We couldn't save settings.<br><br>Details: {exc} | Use plain language; label technical details. |

## `CleanSheet/ui/views/view_t_sources.py`

| Location | Type | Current | Suggested | Notes |
|---|---|---|---|---|
| `CleanSheet/ui/views/view_t_sources.py:112` | UI copy | Transaction Tables | Transaction Tables |  |
| `CleanSheet/ui/views/view_t_sources.py:118` | UI copy | Upload new versions for existing tables, delete obsolete ones, | Replace existing files, remove tables you no longer need, | Trim extra whitespace. Rewrite for clarity. |
| `CleanSheet/ui/views/view_t_sources.py:119` | UI copy | or add new transaction tables. | or add new tables. | Rewrite for clarity. |
| `CleanSheet/ui/views/view_t_sources.py:163` | UI copy | CURRENT TRANSACTION TABLES | Current Transaction Tables | Avoid all-caps headings. |
| `CleanSheet/ui/views/view_t_sources.py:209` | UI copy | No transaction tables added yet. | No transaction tables yet. Add one to get started. | Rewrite for clarity. |
| `CleanSheet/ui/views/view_t_sources.py:260` | UI copy | Transaction table | Transaction table |  |
| `CleanSheet/ui/views/view_t_sources.py:324` | UI copy | Chained transaction · {len(chain)} source{'s' if len(chain) != 1 else ''} | Chained transaction · {len(chain)} source{'s' if len(chain) != 1 else ''} |  |
| `CleanSheet/ui/views/view_t_sources.py:496` | UI copy | Append to Chain | Append to Chain |  |
| `CleanSheet/ui/views/view_t_sources.py:497` | UI copy | Once added, this file cannot be removed individually.<br><br> | Once added, this file cannot be removed individually.<br><br> |  |
| `CleanSheet/ui/views/view_t_sources.py:506` | UI copy | Select Excel file to append | Select Excel file to append |  |
| `CleanSheet/ui/views/view_t_sources.py:506` | UI copy | Excel Files (*.xlsx *.xlsm *.xls) | Excel Files (*.xlsx *.xlsm *.xls) |  |
| `CleanSheet/ui/views/view_t_sources.py:547` | Dialog | Title: Error<br>Body: Could not read file:<br>{exc} | Title: Couldn't read file<br>Body: We couldn't read file.<br><br>Details: {exc}<br><br>Make sure the file exists, is a supported Excel file, and isn't open in Excel, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/views/view_t_sources.py:562` | UI copy | Delete Chained Source | Delete Chained Source |  |
| `CleanSheet/ui/views/view_t_sources.py:563` | UI copy | This will permanently remove the chained table '{table_name}' | This will permanently remove the chained table '{table_name}' | Trim extra whitespace. |
| `CleanSheet/ui/views/view_t_sources.py:596` | Dialog | Title: Error<br>Body: Could not delete source:<br>{exc} | Title: Couldn't delete source<br>Body: We couldn't delete source.<br><br>Details: {exc}<br><br>Make sure the item isn't in use, then try again. | Make the title specific. Use plain language; label technical details. Add a next step. |
| `CleanSheet/ui/views/view_t_sources.py:644` | Dialog | Title: Updated<br>Body: Table '{table_name}' updated. | Title: Updated<br>Body: Table '{table_name}' updated. |  |
| `CleanSheet/ui/views/view_t_sources.py:649` | UI copy | Error | Error |  |
| `CleanSheet/ui/views/view_t_sources.py:649` | UI copy | Could not update table:<br>{exc} | We couldn't update table.<br><br>Details: {exc} | Use plain language; label technical details. |
| `CleanSheet/ui/views/view_t_sources.py:654` | UI copy | Error | Error |  |
| `CleanSheet/ui/views/view_t_sources.py:654` | UI copy | Could not read file:<br>{exc} | We couldn't read file.<br><br>Details: {exc} | Use plain language; label technical details. |
| `CleanSheet/ui/views/view_t_sources.py:666` | UI copy | Confirm Delete | Confirm Delete |  |
| `CleanSheet/ui/views/view_t_sources.py:667` | UI copy | Deleting '{table_name}' will also remove {count} mapping(s). Confirm? | Deleting '{table_name}' will also remove {count} mapping(s).? | Use a direct confirmation question. |
| `CleanSheet/ui/views/view_t_sources.py:694` | UI copy | Error | Error |  |
| `CleanSheet/ui/views/view_t_sources.py:694` | UI copy | Could not delete table:<br>{exc} | We couldn't delete table.<br><br>Details: {exc} | Use plain language; label technical details. |


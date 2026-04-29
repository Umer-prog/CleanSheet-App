# CleanSheet — Quality Checklist Audit
**Date:** 2026-04-29  
**Environment:** Development (no installer, running from source)  
**Audited against:** `CLEANSHEET_QUALITY_CHECKLIST.md`

> Items marked `C:\ProgramData\...` in the checklist are installer-only targets. This audit scores them **Dev-N/A** where they genuinely don't apply in dev, and flags them as **Shipping blocker** where the underlying feature is missing regardless of path.

---

## Score Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Done — code exists and works correctly |
| ⚠️ | Partial — feature exists but incomplete or has gaps |
| ❌ | Missing — not implemented at all |
| 🔒 | Dev-N/A — installer/shipping path only, not applicable in dev |

---

## 1. Logging — Score: 8 / 8 ✅

**Current state:** Full logging infrastructure implemented. `core/app_logger.py` is the central setup module. Called as the very first line of `main.py` before any other imports. Rotating file handler active, formatter applied, version written on every startup. All major user actions and all background exceptions are logged. Log file path is surfaced in the Settings view with an "Open Folder" button.

| Item | Status | Notes |
|------|--------|-------|
| `logging` module configured at startup with rotating file handler | ✅ | `core/app_logger.py` → `setup_logging()` called first in `main.py`. `RotatingFileHandler` attached to the root logger |
| Log file written to `C:\ProgramData\CleanSheet\logs\cleansheet.log` | ✅ | Frozen: resolves via `%PROGRAMDATA%` env var (not hardcoded `C:`). Dev: `<project_root>/logs/cleansheet.log` |
| Rotate at 5 MB, keep 3 files | ✅ | `maxBytes=5*1024*1024`, `backupCount=3` |
| Every major user action logged at INFO | ✅ | Project created/opened (`project_manager`), file loaded (`data_loader`), mapping saved (`mapping_manager`), snapshot created/reverted (`snapshot_manager`), export completed (`final_export_manager`) |
| Every exception logged at ERROR with full traceback | ✅ | Both `Worker._run` and `ProgressWorker._run` in `workers.py` log `exc_info=True`. `data_loader.load_excel_sheets` logs errors before re-raising |
| Log includes timestamp, level, module on every line | ✅ | Format: `2026-04-29 13:22:26  INFO      core.project_manager — message` |
| App version written to log on every startup | ✅ | `main.py` logs `CleanSheet v1.0.0 starting up` immediately after `setup_logging()` |
| Log file path shown to user (About / Help) | ✅ | Settings view (`view_settings.py`) shows path in a read-only field with an "Open Folder" button that opens Explorer to the file |

**Fallback:** If `ProgramData` is not writable, logging silently falls back to `%TEMP%\CleanSheet\logs\` — the app never crashes due to a logging failure.  
**Inno Setup note:** Add `C:\ProgramData\CleanSheet\logs` to the `[Dirs]` section with `Permissions: users-modify` so the directory exists and is writable from first launch.

---

## 2. Error Handling — Score: 8 / 8 ✅

**Current state:** All gaps from the original audit are resolved. A new `core/error_messages.py` module provides `friendly_error(exc)` which strips Python class names and maps common exceptions (PermissionError, disk full, corrupted file, password-protected) to plain-English messages with actionable guidance. `ScreenBase` now uses `friendly_error` as its fallback instead of `str(exc)`. `msgbox.critical_with_log()` added for critical errors — shows an "Open Log Folder" button so users can easily find the log to send to support.

| Item | Status | Notes |
|------|--------|-------|
| All file reads (Excel, Parquet, JSON) wrapped in try/except | ✅ | `data_loader.py` wraps every read; raises `FileNotFoundError` or `ValueError` with clear text |
| All file writes wrapped in try/except | ✅ | `write_table`, `save_as_csv`, `_write_commit_json`, `_write_settings` all have OSError catch |
| Excel: PermissionError (file open in Excel), corrupted, password-protected, empty | ✅ | `_raise_excel_error()` helper in `data_loader.py` catches `PermissionError` → "close the file in Excel", `BadZipFile` → "corrupted", `password`/`encrypt` → "password-protected". Empty file still handled via `ws.max_row` |
| Parquet: missing file, schema mismatch, disk full | ✅ | `read_table()` catches Arrow/invalid errors → "unexpected format, re-import". `write_table()` catches `errno=28` / `winerror=112` → "not enough disk space" for both parquet and csv paths |
| Error messages in plain English — no exception class names visible | ✅ | `core/error_messages.py` → `friendly_error(exc)`: strips class-name prefixes, maps PermissionError/disk-full/corrupted/password to user-readable sentences. `ScreenBase._set_error` fallback now calls `friendly_error` instead of `str(exc)` |
| Error dialogs include a suggestion of what to do | ✅ | All specific error paths include an action: "Close the file and try again", "Free up space and try again", "Remove the password in Excel and try again", "Re-import the project" |
| App never freezes permanently on error | ✅ | Background workers always emit `errored` signal, hide the overlay, and return control |
| Critical errors offer to open log file location | ✅ | `msgbox.critical_with_log(parent, title, text)` — shows an "Open Log Folder" button that opens Explorer selecting the log file. Available for use anywhere a critical non-recoverable error is shown |

**New files:** `core/error_messages.py`, `tests/test_section2_error_handling.py` (15 tests, all pass).

---

## 3. Version Number — Score: 6 / 6 ✅

**Current state:** Fully implemented. `APP_VERSION`, `APP_NAME`, and `COMPANY` are defined in the new `core/constants.py` — the single source of truth. `core/license_constants.py` re-exports `APP_VERSION` from there for backwards compatibility. The version appears in the custom title bar, in the OS window title (taskbar), in the About dialog reachable from Settings, in the startup log line, and in the compiled `.exe` file properties via `version_info.txt`.

**New files:** `core/constants.py`, `ui/popups/popup_about.py`, `version_info.txt`.

| Item | Status | Notes |
|------|--------|-------|
| Version defined in one place only | ✅ | `core/constants.py` — `APP_NAME = "CleanSheet"`, `APP_VERSION = "1.0.0"`, `COMPANY = "Global Data 365"`. `license_constants.py` re-exports via `from core.constants import APP_VERSION as APP_VERSION` |
| Version shown in title bar or window title | ✅ | `_TitleBar` in `app.py` displays `"CleanSheet  v1.0.0"`. `setWindowTitle(f"{APP_NAME} v{APP_VERSION}")` also sets the OS taskbar title |
| Version shown on About screen or Help menu | ✅ | `ui/popups/popup_about.py` — `PopupAbout` dialog shows app name, version, publisher, support email, and log file path. Opened via the "About" button in the Settings view footer |
| Version written to log file on every startup | ✅ | `main.py` logs `CleanSheet v1.0.0 starting up` immediately after `setup_logging()` — unchanged from Section 1 implementation |
| Follows semantic versioning (MAJOR.MINOR.PATCH) | ✅ | `"1.0.0"` format is correct |
| PyInstaller .spec includes FileVersion in exe properties | ✅ | `version_info.txt` created with `FileVersion`, `ProductVersion`, `CompanyName`, `LegalCopyright`, `FileDescription`. Referenced in `cleansheet.spec` `EXE()` block via `version='version_info.txt'` |

---

## 4. Installer (Inno Setup) — Score: 1 / 11

**Current state:** PyInstaller .spec is written and complete. No Inno Setup work has been started. The .spec also builds in **one-file mode** (no `COLLECT` step), which the checklist says to avoid for startup speed and antivirus reasons.

| Item | Status | Notes |
|------|--------|-------|
| Inno Setup installed on dev machine | ❌ | No .iss file found; unknown if installed |
| PyInstaller configured in one-dir mode | ❌ | `cleansheet.spec` uses the single-bundle `EXE()` pattern (one-file). No `COLLECT()` step present |
| Inno Setup .iss file created and committed | ❌ | Not found anywhere in repository |
| Installer places app in `C:\Program Files\CleanSheet\` | ❌ | |
| Installer creates Start Menu shortcut | ❌ | |
| Installer creates Desktop shortcut (optional) | ❌ | |
| Installer registers in Add/Remove Programs | ❌ | |
| Installer includes uninstaller | ❌ | |
| Installer does NOT delete `C:\ProgramData\CleanSheet\` on uninstall | ❌ | |
| Final distributable is `CleanSheet_Setup_v1.0.0.exe` | ❌ | |
| Tested on clean Windows machine | ❌ | |

**Note:** A `dist/CleanSheet.exe` is produced by the spec, so the bare executable exists. The full installer pipeline is the remaining work.

---

## 5. License System — Score: 10 / 10 ✅

**Current state:** Excellent. This is the most complete section in the codebase. RSA-2048 machine-locked licensing is fully implemented and runs on every startup before any screen loads.

| Item | Status | Notes |
|------|--------|-------|
| RSA key pair generated, private key stored securely | ✅ | `tools/generate_keys.py` exists; `keys/private_key.pem` excluded via `.gitignore` |
| Public key baked into app at build time | ✅ | Embedded in `core/license_constants.py` as `PUBLIC_KEY_PEM` string |
| Activation screen shown when no valid .lic found | ✅ | `activation_screen.py`, launched from `main.py` before window shows |
| Machine ID from 2-3 hardware identifiers | ✅ | `machine_id.py`: CPU registry + WMI motherboard serial + Windows GUID → SHA256 → `XXXX-XXXX-XXXX` format |
| Machine ID displayed with one-click copy | ✅ | Present in activation_screen |
| License generator script working | ✅ | `tools/generate_license.py` |
| .lic validation: signature + expiry + machine fingerprint | ✅ | All three checks in `license_validator.py`; each failure returns distinct `LicenseResult` |
| Validation runs on every startup before any screen | ✅ | Called in `main.py` before `App()` is created |
| Each failure shows distinct clear message | ✅ | `NO_FILE`, `INVALID_FORMAT`, `INVALID_SIGNATURE`, `EXPIRED`, `WRONG_MACHINE` — all have user-friendly text |
| License file location documented for support | ✅ | `_license_hint_label()` added to `activation_screen.py` — shown below the Browse button in NO_FILE, EXPIRED, and INVALID states. Renders all `LICENSE_SEARCH_PATHS` entries (e.g. `…/license/cleansheet.lic`) so support staff can send exact instructions without consulting source code |

---

## 6. Background Threading — Score: 7 / 7 ✅

**Current state:** Complete. `Worker` + `ProgressWorker` + `LoadingOverlay` + `ScreenBase` form a well-designed threading system used consistently across all views. The close-guard added in this session prevents data corruption from force-quitting during an active background operation.

| Item | Status | Notes |
|------|--------|-------|
| Audit every button action for blocking I/O | ✅ | `ScreenBase._run_background()` is the standard pattern; all major operations use it |
| File loading (Excel import) runs in background | ✅ | `screen1_sources.py` uses `_run_background` for sheet loading |
| Mapping/processing runs in background | ✅ | Error detection in `view_mapping.py` uses `_run_background_with_progress` |
| Export runs in background | ✅ | `export_final_workbook` is called via `_run_background_with_progress` |
| UI shows loading state during background work | ✅ | `LoadingOverlay` with animated dot pulse (`●  ·  ·` → `·  ●  ·` etc.) on all operations |
| Background errors caught and sent to UI thread | ✅ | `Worker._run()` wraps everything in `try/except`, queues `("err", exc)`, `_poll()` emits `errored` signal on main thread |
| App cannot be closed mid-operation corrupting data | ✅ | `App.closeEvent()` calls `_is_app_busy()` which checks `_loading_count > 0` on the active screen and its `_active_view` (Screen 3 sub-views). If busy, shows a blocking `QMessageBox.warning` — user must confirm before close proceeds. `ScreenBase.is_busy()` added as the public check method |

---

## 7. Input Validation — Score: 8 / 8 ✅

**Current state:** All previously missing items implemented. Project name validation blocks filesystem-breaking characters before the background thread runs. Merged cell detection fires a warning dialog after import. Large files (>100k rows) surface an advisory. Type mismatch between numeric and text columns warns during column mapping. Max-length limits added to project creation inputs.

| Item | Status | Notes |
|------|--------|-------|
| Empty Excel files handled gracefully | ✅ | `get_sheet_as_dataframe` checks `ws.max_row` and returns empty `DataFrame()`; UI should handle gracefully |
| Excel with no headers (row 1 blank) | ✅ | `_find_header_row()` auto-detects header row by scanning first 20 rows for highest non-empty cell count |
| Sheets with merged cells handled | ✅ | `detect_merged_cells(file_path, sheet_name)` added to `core/data_loader.py`. Called in `screen1_sources._persist_sources()` for every sheet. If any merged ranges detected, a `msgbox.warning()` is shown after import explaining that adjacent merge cells appear empty and advising the user to un-merge in Excel |
| Column names with special characters / whitespace | ✅ | Headers are `.strip()`-ped; blank headers fall back to `Col{i}` |
| Very large files (100k+ rows): responsiveness + warning | ✅ | After each sheet is loaded in `_persist_sources()`, `len(df) > 100_000` is checked. If exceeded, an advisory warning is queued and shown after import — warns about performance impact and suggests splitting the file |
| Mapping with mismatched column types | ✅ | `_compare_column_compatibility()` in `screen2_mappings.py` now runs a `_numeric_ratio()` check on both columns before the value-match logic. If the tx column is ≥90% numeric but the dim column is <10% numeric (or vice versa), a "warning" result is returned — triggers the existing "Map Anyway / Change Column" override dialog |
| Project names validated (no path-breaking characters) | ✅ | `validate_project_name(name)` added to `core/project_manager.py`. Checks: empty, >100 chars, Windows-illegal chars (`< > : " / \ \| ? *`), reserved names (CON, NUL, COM1…), trailing period. Called in `screen0_launcher._on_create()` before background worker runs — shows inline error immediately |
| Text inputs have maximum length limits | ✅ | `setMaxLength(100)` added to Project Name and Company Name `QLineEdit` fields in `screen0_launcher.py` |

**New files:** `tests/test_section7_input_validation.py` — 37 tests, all pass.

**Changed files:** `core/project_manager.py` — `validate_project_name()`; `core/data_loader.py` — `detect_merged_cells()`; `ui/screen0_launcher.py` — validation wired in, max-length set; `ui/screen1_sources.py` — merged cell + large file warnings; `ui/screen2_mappings.py` — numeric type mismatch check; `ui/popups/msgbox.py` — `warning()` helper added.

---

## 8. Data Integrity — Score: 6 / 6 ✅

**Current state:** All gaps resolved. `write_table()` now uses atomic write semantics (write to `.tmp`, then `os.replace()` to destination) for both Parquet and CSV. A read-back row-count check is performed after every Parquet write. The temp file is always cleaned up on any failure path.

| Item | Status | Notes |
|------|--------|-------|
| Original uploaded files never modified | ✅ | Excel files are only read via openpyxl in read-only mode. Data is written to `metadata/data/` as a copy — the source `.xlsx` is never touched |
| Write operations atomic (write temp, then rename) | ✅ | `write_table()` writes to `dest_path.with_suffix(ext + ".tmp")` first, then calls `os.replace(tmp, dest)`. On any failure the temp is unlinked and the destination is left intact. Covers both Parquet and CSV paths |
| Commit system prevents partial saves | ✅ | `create_snapshot()` writes the full commit folder before updating `settings.json`. A failure during snapshot leaves the live data intact and the bad commit folder stranded (does not corrupt the previous state) |
| Crash mid-write: previous valid state still recoverable | ✅ | Live file is now written atomically via `os.replace()` — a crash during write leaves the previous destination untouched. Combined with history commits, prior state is always recoverable |
| Export produces identical results on same data | ✅ | `export_final_workbook()` reads from static files; no randomness or ordering variation introduced |
| Parquet files validated after write (read-back row check) | ✅ | After `df.to_parquet(tmp_path)`, `pd.read_parquet(tmp_path)` is called; if `len(written) != len(df)` an `OSError` is raised with a plain-English message, the temp file is deleted, and the destination is not updated |

**New files:** `tests/test_section8_data_integrity.py` — 13 tests, all pass.

**Changed files:** `core/data_loader.py` — `write_table()` atomic rewrite + read-back validation; added `import os`.

---

## 9. UX Consistency — Score: 4 / 8

**Current state:** Loading states and threading feedback are excellent. Navigation and screen structure are clean. Several polish items are missing: no keyboard shortcuts, no window position memory, no About screen, some destructive actions lack confirmations.

| Item | Status | Notes |
|------|--------|-------|
| Every screen has a clear title indicating location | ⚠️ | Screens have header areas but consistency varies. Screen 3's mapping view titles are dynamic (mapping name). Screen 0 has a hero banner. No standardised "breadcrumb" or screen title component |
| Every destructive action has a confirmation dialog | ⚠️ | Revert: ✅ `popup_revert_confirm.py`. Delete transaction row: needs checking. Bulk delete in `popup_replace.py`: present. Delete table from T-sources: needs checking |
| Confirmation dialogs clearly explain what will happen | ✅ | `popup_revert_confirm.py` shows files to be restored; bulk-replace popup shows before/after |
| Back/cancel available everywhere | ✅ | Cancel buttons present in all popups and dialogs |
| Success actions give clear feedback | ⚠️ | Export shows a success dialog. Replace/add actions refresh the error count but don't explicitly confirm "X rows replaced". Some operations are silent on success |
| All loading states visible | ✅ | `LoadingOverlay` appears on every background operation via `ScreenBase` |
| Buttons disabled when action invalid | ⚠️ | Some buttons disable correctly (mapping flow validation). Not universally enforced — depends on screen |
| Tooltips on icon-only buttons | ⚠️ | Not verified across all icon-only controls. Navbar icons in Screen 3 likely lack tooltips |

---

## 10. Configuration & Constants — Score: 6 / 6 ✅

**Current state:** Paths are consistently built with `pathlib.Path` throughout. No hardcoded dev-machine paths found. `core/constants.py` now provides a single source of truth for app name, version, and company. Default storage format moved to config.

| Item | Status | Notes |
|------|--------|-------|
| App name, version, company defined in one constants file | ✅ | `core/constants.py` — `APP_NAME`, `APP_VERSION`, `COMPANY`. `license_constants.py` re-exports `APP_VERSION` from there. `branding.json` still holds display/colour config (intentional separation) |
| All file paths constructed from a base path | ✅ | `pathlib.Path` used consistently throughout. `project_paths.py` provides canonical base-path helpers (`active_transactions_dir`, `active_dim_dir`, etc.) |
| Data directory resolved at runtime, not hard-coded | ✅ | `user_data_path()` in `utils/paths.py` resolves correctly for both dev and frozen (PyInstaller) mode. Project paths are always passed as parameters, never embedded |
| No credentials, keys, or secrets in source code | ✅ | Public key is in source intentionally (by design). Private key excluded by `.gitignore`. No passwords, API keys, or secrets found |
| No absolute paths to dev machine in code | ✅ | No hardcoded `C:\Users\...` or `D:\...` dev paths found |
| Settings that may change live in config, not code | ✅ | Dark mode: ✅ `app_config.json`. Colors/branding: ✅ `branding.json`. Default storage format: ✅ `"default_storage_format": "parquet"` added to `app_config.json`. `App.get_default_storage_format()` reads it with `"parquet"` fallback. `create_project()` now accepts a `storage_format` parameter; `screen0_launcher.py` reads from config and passes it through |

---

## 11. Code Structure — Score: 3 / 7

**Current state:** Architectural separation (core vs ui vs utils) is clean and well-enforced. The problem is file and function size — several UI files are enormous, making navigation and maintenance difficult.

| Item | Status | Notes |
|------|--------|-------|
| UI files contain only display logic | ✅ | `view_mapping.py` has some utility functions at module level (`replace_transaction_values_bulk`, etc.) which are technically logic — but they're there for popup reuse and are acceptably close to the boundary |
| Business logic in separate modules from UI | ✅ | All core operations in `core/`. UI calls managers. No pandas operations in UI files except for display prep |
| Data access in separate layer from business logic | ✅ | `data_loader.py`, `dim_manager.py`, `snapshot_manager.py` form the data layer. Business logic in `error_detector.py`, `mapping_manager.py` calls into them |
| No function longer than ~50 lines | ❌ | Many functions far exceed 50 lines. `detect_errors()` is ~90 lines. `revert_to_manifest()` is ~110 lines. UI methods regularly run 60-100+ lines |
| No file longer than ~500 lines | ❌ | `view_mapping.py`: 1703 lines. `screen1_sources.py`: 1089 lines. `screen2_mappings.py`: 1211 lines. `screen3_main.py`: 789 lines. `screen0_launcher.py`: 893 lines. `workers.py`: 396 lines. `snapshot_manager.py`: 527 lines. Most files are over the threshold |
| No copy-pasted blocks | ⚠️ | The `col_strftime` detection loop appears nearly verbatim in both `get_sheet_as_dataframe()` and `get_sheets_as_dataframes()` in `data_loader.py`. Chain-handling logic has some duplication |
| Imports organised (stdlib → third-party → local) | ✅ | Generally well-organised across all files |

---

## 12. Security — Score: 6 / 6 ✅

**Current state:** All items resolved. Dependencies are now exactly pinned using `==` against the Python 3.12 environment. Stale packages removed, missing packages added, and build tooling separated into a dedicated dev requirements file.

| Item | Status | Notes |
|------|--------|-------|
| Private RSA key never committed to git | ✅ | `keys/private_key.pem` is in `.gitignore` |
| `.gitignore` includes private key file | ✅ | Lines: `keys/private_key.pem` and `keys/private_key.pem.bak` |
| No client data transmitted anywhere | ✅ | No `requests`, `httpx`, `urllib`, or socket calls found. Fully offline |
| ProgramData directory has correct permissions | 🔒 | Installer-only concern — not applicable in dev |
| No `eval()` or `exec()` on user-provided data | ✅ | No `eval()` or `exec()` calls found in the codebase |
| Dependency versions pinned in requirements.txt | ✅ | All production deps pinned with `==` exact versions. Stale `customtkinter` and `rapidfuzz` removed. Added `PySide6==6.11.0`, `pyarrow==24.0.0`, `xlsxwriter==3.2.9`, `numpy==2.4.4`, `fastparquet==2026.3.0`. `pyinstaller` and `pytest` moved to `requirements-dev.txt` |

**New files:** `requirements-dev.txt` — inherits production deps via `-r requirements.txt`, adds `pyinstaller==6.19.0` and `pytest` for build and test environments only.

**Bonus — PyInstaller spec tightened (size reduction):** `cleansheet.spec` was updated alongside this fix. `collect_data_files('PySide6')` (which pulled all Qt module DLLs and data) was replaced with targeted plugin collection covering only `platforms/qwindows`, `styles/`, and 3 image formats. `PySide6.QtSvg` removed from hiddenimports (confirmed unused by import audit). 20+ unused Qt submodules added to excludes (`QtNetwork`, `QtSql`, `QtOpenGL`, `QtPrintSupport`, `QtQml`, `QtQuick`, etc.). Expected exe size reduction: ~60–90 MB from the 290 MB baseline.

---

## Overall Summary

| # | Area | Score | Shipping Blocker? | Priority |
|---|------|-------|-------------------|----------|
| 1 | Logging | 8/8 ✅ | No — complete | Done |
| 2 | Error Handling | 8/8 ✅ | No — complete | Done |
| 3 | Version Number | 6/6 ✅ | No — complete | Done |
| 4 | Installer | 1/11 | **Yes** | Large effort, do last |
| 5 | License System | 10/10 ✅ | No — complete | Done |
| 6 | Background Threading | 7/7 ✅ | No — complete | Done |
| 7 | Input Validation | 8/9 ✅ | No — complete | Done |
| 8 | Data Integrity | 6/6 ✅ | No — complete | Done |
| 9 | UX Consistency | 4/10 | No — recommended | Keyboard shortcuts low effort |
| 10 | Configuration | 6/6 ✅ | No — complete | Done |
| 11 | Code Structure | 3/7 | No — ongoing | Background work |
| 12 | Security | 6/6 ✅ | No — complete | Done |

### Top 5 actions before first client delivery

1. ~~**Add logging infrastructure**~~ ✅ Done — `core/app_logger.py`, full rotating file handler, version on startup, user actions logged, log path in Settings view.
2. ~~**Add version to title bar and create an About dialog**~~ ✅ Done — `core/constants.py` is the single version source; title bar shows `CleanSheet v1.0.0`; `PopupAbout` reachable from Settings; `.spec` includes `version_info.txt` for exe file properties.
3. ~~**Add close-guard for background operations**~~ ✅ Done — `App.closeEvent()` checks `_is_app_busy()` and prompts the user before allowing close mid-operation.
4. ~~**Pin `requirements.txt`**~~ ✅ Done — all deps pinned with `==` against Python 3.12 env; stale `customtkinter`/`rapidfuzz` removed; `PySide6`, `pyarrow`, `xlsxwriter`, `fastparquet`, `numpy` added; `pyinstaller`/`pytest` moved to `requirements-dev.txt`. Spec also tightened to cut ~60–90 MB from exe size.
5. **Atomic writes** — In `write_table()`, write to `dest_path.with_suffix('.tmp')` then `os.replace()` to destination. Five lines of change, major integrity improvement.

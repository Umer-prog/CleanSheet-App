# CleanSheet — Professional App Quality Checklist

A practical audit framework for CleanSheet. Work through each section, mark items as you complete them. Priority order is intentional — top sections have highest impact for a shipping product.

---

## 1. Logging

The single most impactful thing you can add before first client delivery. Without logs you are debugging blind when a client reports an issue.

- [ ] Python `logging` module configured at app startup with a rotating file handler
- [ ] Log file written to `C:\ProgramData\CleanSheet\logs\cleansheet.log`
- [ ] Log rotates at 5MB, keeps last 3 files (prevents disk fill)
- [ ] Every major user action logged at INFO level (project created, file loaded, mapping saved, export completed)
- [ ] Every exception logged at ERROR level with full traceback
- [ ] Log includes timestamp, log level, module name on every line
- [ ] App version written to log on every startup
- [ ] Log file path shown somewhere accessible to user (About screen or Help menu) so they can find it to send to you

---

## 2. Error Handling

Every place the app touches external resources must have a try/except. Users must never see a Python traceback.

- [ ] All file reads (Excel, Parquet, JSON) wrapped in try/except with user-facing message
- [ ] All file writes wrapped in try/except — failure should not silently corrupt data
- [ ] Excel files specifically: handle file open in another program (PermissionError), corrupted file, password-protected file, empty file
- [ ] Parquet operations: handle missing file, schema mismatch, disk full
- [ ] All error messages shown to user in plain English — no exception class names visible
- [ ] Error dialogs include a suggestion of what to do (e.g. "Close the file in Excel and try again")
- [ ] App never freezes permanently on an error — always returns to a usable state
- [ ] Critical errors that cannot recover offer to open the log file location for the user

---

## 3. Version Number

Low effort, high professionalism signal. Essential for support.

- [ ] Version number defined in one place only (e.g. `constants.py` or `__version__.py`)
- [ ] Version shown in title bar or window title (e.g. `CleanSheet v1.0.0`)
- [ ] Version shown on About screen or Help menu
- [ ] Version written to log file on every startup
- [ ] Version follows semantic versioning: MAJOR.MINOR.PATCH
  - MAJOR: breaking changes or major new features
  - MINOR: new features, backward compatible
  - PATCH: bug fixes only
- [ ] PyInstaller build includes version in the exe file properties (FileVersion field in .spec)

---

## 4. Installer (Inno Setup)

Clients should never receive a raw .exe or folder. They should receive a Setup.exe.

- [ ] Inno Setup installed on your dev machine
- [ ] PyInstaller configured in one-dir mode (not one-file) — faster startup, no antivirus issues
- [ ] Inno Setup script (.iss file) created and committed to your project
- [ ] Installer places app in `C:\Program Files\CleanSheet\`
- [ ] Installer creates Start Menu shortcut
- [ ] Installer creates Desktop shortcut (optional, user choice during install)
- [ ] Installer registers app in Windows Add/Remove Programs with correct name, version, publisher
- [ ] Installer includes an uninstaller that cleanly removes all app files
- [ ] Installer does NOT delete user data in `C:\ProgramData\CleanSheet\` on uninstall (preserve projects)
- [ ] Final distributable is a single `CleanSheet_Setup_v1.0.0.exe`
- [ ] Tested: install on a clean Windows machine that has never had Python installed

---

## 5. License System

Covered in full in `LICENSE_SYSTEM_IMPLEMENTATION.md`. Summary checklist here.

- [ ] RSA key pair generated and private key stored securely (not in project repo)
- [ ] Public key baked into app at build time
- [ ] Activation screen shown when no valid .lic file found
- [ ] Machine ID correctly generated from 2-3 hardware identifiers
- [ ] Machine ID displayed clearly with one-click copy
- [ ] License generator script working and tested
- [ ] .lic file validation: signature check, expiry check, machine fingerprint check
- [ ] Validation runs on every app startup before any screen loads
- [ ] Each check failure shows a distinct, clear message to the user
- [ ] License file location documented for support purposes

---

## 6. Background Threading

Any operation that takes more than ~1 second must not run on the main UI thread. A frozen window looks like a crash to a client.

- [ ] Audit every button action — identify anything that reads/writes files or processes data
- [ ] File loading (Excel import) runs in QThread or via QThreadPool
- [ ] Mapping/processing operations run in background thread
- [ ] Export to Excel runs in background thread
- [ ] UI shows a loading state (spinner, progress bar, or disabled controls) during background work
- [ ] Background thread errors are caught and communicated back to the UI thread safely
- [ ] App cannot be closed mid-operation in a way that corrupts data (disable close or warn user)

---

## 7. Input Validation

Client data is always dirty. Validate before processing, not after crashing.

- [ ] Empty Excel files handled gracefully (clear message, not crash)
- [ ] Excel files with no headers handled (row 1 is blank)
- [ ] Sheets with merged cells handled or detected and reported
- [ ] Column names with special characters or whitespace handled
- [ ] Very large files (100k+ rows): does the app remain responsive? Is there a warning?
- [ ] Dimension tables with duplicate values flagged to the user
- [ ] Mapping attempted with mismatched column types handled
- [ ] Project names validated: no special characters that break file paths
- [ ] All text inputs have maximum length limits to prevent unexpected behaviour

---

## 8. Data Integrity

Your app modifies client data. Errors here are the most damaging.

- [ ] Original uploaded files are never modified — always work from copies
- [ ] Write operations are atomic where possible (write to temp file, then rename)
- [ ] Commit system (already in architecture) prevents partial saves
- [ ] If app crashes mid-write, the previous valid state is still recoverable
- [ ] Export produces identical results when run twice on the same data (deterministic)
- [ ] Parquet files validated after write (read back and check row count)

---

## 9. User Experience Consistency

Polish signals professionalism to non-technical clients.

- [ ] Every screen has a clear title indicating where the user is
- [ ] Every destructive action (delete, overwrite) has a confirmation dialog
- [ ] Confirmation dialogs clearly explain what will happen
- [ ] Back/cancel is available everywhere it makes sense
- [ ] Success actions give clear feedback (not just silence)
- [ ] All loading states are visible — no operation appears to hang
- [ ] Keyboard shortcuts for common actions (Ctrl+S, Escape to cancel)
- [ ] Window remembers its last position and size between sessions
- [ ] All buttons are disabled when their action is not currently valid (not just hidden)
- [ ] Tooltips on icon-only buttons or non-obvious controls

---

## 10. Configuration & Constants

Hard-coded values scattered through code is fragile and hard to maintain.

- [ ] App name, version, company name defined in one constants file
- [ ] All file paths constructed from a base path, never hard-coded strings
- [ ] Data directory (`C:\ProgramData\CleanSheet\`) resolved at runtime, not hard-coded
- [ ] No credentials, keys, or secrets anywhere in source code
- [ ] No absolute paths to your dev machine anywhere in code
- [ ] Settings that may change (e.g. default export format) live in config, not scattered in code

---

## 11. Code Structure

Lower urgency than the above, but important as the codebase grows.

- [ ] UI files contain only display logic — no data processing inside event handlers
- [ ] Business logic (mapping engine, validation rules) in separate modules from UI
- [ ] Data access (reading/writing Parquet, JSON) in separate layer from business logic
- [ ] No function longer than ~50 lines — split into smaller named functions
- [ ] No file longer than ~500 lines — split into modules
- [ ] No copy-pasted blocks of code — extract to a shared function
- [ ] Imports organised: standard library, then third-party, then local

---

## 12. Security

- [ ] Private RSA key never committed to git repository
- [ ] `.gitignore` includes the private key file
- [ ] No client data transmitted anywhere — app is fully offline
- [ ] ProgramData directory has correct permissions (app can write, but not world-readable by default)
- [ ] No eval() or exec() calls on any user-provided data
- [ ] Dependency versions pinned in requirements.txt to prevent unexpected upgrades

---

## Release Checklist

Run through this before every client delivery.

- [ ] Version number incremented appropriately
- [ ] Tested on a clean Windows machine (not your dev machine)
- [ ] All known bugs from previous version resolved or documented
- [ ] Log file confirmed working on clean machine
- [ ] License system tested: activation, expiry block, wrong machine block
- [ ] Installer tested: install, launch, uninstall
- [ ] Export tested with a real client-like dataset
- [ ] No Python or debug output visible to user anywhere
- [ ] File size of Setup.exe is reasonable (document if over 100MB)

---

## Priority Summary

| # | Area | Effort | Do Before First Client |
|---|------|--------|------------------------|
| 1 | Logging | Low | Yes |
| 2 | Error handling | Medium | Yes |
| 3 | Version number | Very low | Yes |
| 4 | Installer | Low | Yes |
| 5 | License system | Medium | Yes |
| 6 | Background threading | Medium | Recommended |
| 7 | Input validation | Medium | Recommended |
| 8 | Data integrity | Low-Medium | Yes |
| 9 | UX consistency | Low | Recommended |
| 10 | Configuration | Low | Recommended |
| 11 | Code structure | High | No — ongoing |
| 12 | Security | Low | Yes |

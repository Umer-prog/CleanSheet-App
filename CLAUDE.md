# Workfolio — Claude Code Instructions

## What this project is
A desktop data standardization app built in Python + CustomTkinter.
Clients load Excel files, define column mappings between transaction and dimension tables,
and the app detects and resolves data inconsistencies (spelling errors, whitespace, wrong values).
Full spec is in `docs/SPEC.md` — read it before starting any section.

## Rules — always follow these

### Language & libraries
- Python 3.11+
- UI: customtkinter only (no tkinter directly unless customtkinter doesn't support it)
- Excel: pandas + openpyxl
- Fuzzy matching: rapidfuzz (available but not in scope yet — don't add it prematurely)
- No external UI frameworks, no web tech, no flask/fastapi

### File storage rules
- Dimension tables → JSON files in `data/dim/`
- Transaction tables → CSV files in `data/transactions/`
- Manifests → folders inside `history/`, each with a `manifest.json`
- Mappings → single `mappings/mapping_store.json`
- Project config → `project.json` at project root
- Settings → `settings.json` at project root

### Code structure rules
- One class per screen/view (e.g. `Screen1DataSources`, `Screen3Main`)
- All file I/O goes through dedicated manager classes (never write files directly from UI code)
- Manager classes live in `core/` folder
- UI classes live in `ui/` folder
- No business logic inside UI classes — UI calls managers, managers do the work
- Every manager method that writes to disk must be wrapped in try/except

### Naming conventions
- Files: snake_case
- Classes: PascalCase
- Methods/variables: snake_case
- Constants: UPPER_SNAKE_CASE

### Window size
- Fixed window size: **1280×720** (not resizable, not full screen)
- Set via `app.geometry("1280x720")` and `app.resizable(False, False)`
- Never maximise or go full screen by default
- All layouts must be designed to fit and look correct at 1280×720

### Screen navigation
- Use frame switching (not full window reload)
- Each screen is a CTkFrame subclass
- Navigation controller manages which frame is visible
- Never use global variables for state — pass state through the navigation controller

### Error handling
- All disk operations: try/except with user-facing error dialogs (CTkMessagebox or similar)
- Never silently swallow exceptions
- Validation errors shown as inline labels (red text), not popups, unless it's a blocking action

### Do not
- Do not use tkinter StringVar/IntVar etc unless absolutely necessary
- Do not put SQL or file I/O inside UI files
- Do not hardcode paths — always use pathlib.Path
- Do not skip validation steps defined in the spec

## Project folder structure (code)
```
workfolio/
  main.py                        ← entry point, launches app
  core/
    project_manager.py           ← create/open/list projects
    snapshot_manager.py          ← manifests, hashing, history, revert
    mapping_manager.py           ← read/write/validate mappings
    data_loader.py               ← read Excel, parse sheets
    error_detector.py            ← compare transaction vs dim columns
    dim_manager.py               ← read/append dim JSON files
  ui/
    app.py                       ← main CTk window, navigation controller
    screen0_launcher.py          ← project launcher
    screen1_sources.py           ← add data sources
    screen2_mappings.py          ← define mappings
    screen3_main.py              ← main working screen (navbar + content)
    views/
      view_mapping.py            ← mapping error view
      view_t_sources.py          ← transaction sources management
      view_d_sources.py          ← dimension sources management
      view_history.py            ← history / revert view
      view_settings.py           ← settings view
    popups/
      popup_sheet_selector.py    ← Power BI style sheet picker
      popup_replace.py           ← replace error value
      popup_add.py               ← add new dim row
      popup_revert_confirm.py    ← revert confirmation
  docs/
    SPEC.md                      ← full project specification
  tests/
    test_snapshot_manager.py
    test_mapping_manager.py
    test_error_detector.py
```

## Build sections (do one at a time)

Each section below is self-contained and can be built in a separate session.
Complete each section fully before moving to the next.

### Section 1 — Core foundation (no UI)
Files: `core/project_manager.py`, `core/data_loader.py`, folder structure creation
Goal: Create a new project on disk, load an Excel file and list its sheets, save a sheet as CSV or JSON
Test: `tests/test_project_manager.py`

### Section 2 — Snapshot system (no UI)
Files: `core/snapshot_manager.py`
Goal: Hash a dataframe, create a manifest, save files, revert to a manifest, handle history on/off
Test: `tests/test_snapshot_manager.py`

### Section 3 — Mapping and error detection (no UI)
Files: `core/mapping_manager.py`, `core/error_detector.py`, `core/dim_manager.py`
Goal: Save/read mappings, compare transaction column vs dim column, return list of errors, append dim row
Test: `tests/test_mapping_manager.py`, `tests/test_error_detector.py`

### Section 4 — UI shell + Screen 0
Files: `ui/app.py`, `ui/screen0_launcher.py`, `main.py`
Goal: App launches, shows project list, new project dialog works, opens existing project
Depends on: Section 1

### Section 5 — Screen 1 (data sources)
Files: `ui/screen1_sources.py`, `ui/popups/popup_sheet_selector.py`
Goal: Add Excel files, sheet picker popup, categorize sheets, validation, navigate to Screen 2
Depends on: Section 1, Section 4

### Section 6 — Screen 2 (define mappings)
Files: `ui/screen2_mappings.py`
Goal: Select dim/transaction tables, select columns, build mapping list, validate all sheets mapped, finish setup
Depends on: Section 3, Section 5

### Section 7 — Screen 3 shell + navbar
Files: `ui/screen3_main.py`
Goal: Left navbar renders, frame switching works, all nav items switch views correctly
Depends on: Section 4

### Section 8 — Mapping error view
Files: `ui/views/view_mapping.py`, `ui/popups/popup_replace.py`, `ui/popups/popup_add.py`
Goal: Show transaction data, show error list, Replace flow, Add flow
Depends on: Section 3, Section 7

### Section 9 — T Sources and D Sources views
Files: `ui/views/view_t_sources.py`, `ui/views/view_d_sources.py`
Goal: List tables, upload new version, delete (T only), add new table, duplicate name check (D)
Depends on: Section 2, Section 7

### Section 10 — History and Settings views
Files: `ui/views/view_history.py`, `ui/views/view_settings.py`, `ui/popups/popup_revert_confirm.py`
Goal: Show manifest list with labels, revert works, settings save correctly
Depends on: Section 2, Section 7

## How to start a new session
Tell Claude Code:
> "Read CLAUDE.md and docs/SPEC.md first. We are working on Section X. 
>  Here is what is already built: [list files done]. Start from where we left off."

---

## UI styling rules (mandatory)

These patterns were approved during Section 4 and must be followed in all future UI screens.

### Screen layout
- Every screen is a two-zone layout: **left sidebar** (fixed width, `sidebar_bg`) + **right content area** (`secondary`)
- Sidebar width: 340px for Screen 0/3 navbar; adjust per screen but keep consistent within a section
- Content area fills remaining space with `weight=1` on the column
- Use `grid` on the top-level frame, `pack` inside panels

### Modals / dialogs (CTkToplevel)
- Size: **520×440** minimum — never smaller, buttons will be cut off
- Structure (always in this order using `pack side=`):
  1. **Header bar** — `side="top"`, height=68, `fg_color=theme.get("primary")`, title in `text_light`, subtitle smaller
  2. **Footer bar** — `side="bottom"`, height=68, `fg_color=theme.get("secondary")`, holds action buttons + inline error label
  3. **Body** — `fill="both", expand=True`, white card (`fg_color="white"`, `corner_radius=10`), holds form fields
- Footer is packed before body so it is always pinned to the bottom regardless of content height
- Error messages appear in the **footer left**, never as a popup
- Action buttons: primary solid on right, outlined cancel to its left, both `height=38`
- Always `transient(parent)` + `grab_set()` to make modal
- Always `self.after(50, self.lift)` to ensure it appears on top

### Form fields inside dialogs
- Use `grid` inside the white body card for label + entry pairs
- Labels: `font=CTkFont(size=12, weight="bold")`, `text_color=theme.get("text_dark")`
- Entries: `height=38`, `corner_radius=8`, `border_color=theme.get("primary")`, with `placeholder_text`
- Path rows (entry + browse button): entry takes remaining width via `columnconfigure(0, weight=1)`, button fixed width 90px

### Buttons
- Primary action: `fg_color=theme.get("primary")`, `text_color=theme.get("text_light")`, `corner_radius=8`, `height=38–46`
- Secondary / cancel: `fg_color="transparent"`, `border_width=1`, `border_color=theme.get("primary")`, `text_color=theme.get("primary")`
- Disabled state: keep the outlined style, set `state="disabled"`

### Project / item cards (sidebar lists)
- Default state: `fg_color="transparent"`, text `theme.get("text_light")`
- Selected state: `fg_color="white"`, text `theme.get("primary")`
- Cursor: `cursor="hand2"` on the card frame
- Bind `<Button-1>` to the frame AND all child labels

### Window icon
- Set in `App._set_icon()`, called via `self.after(100, self._set_icon)`
- **Must use `iconbitmap()` with a real `.ico` file** — `iconphoto()` is overridden by CTk on Windows and does not stick
- Convert PNG → ICO via PIL: `img.convert("RGBA").resize((32,32)).save(ico_path, format="ICO")`
- Save ICO to `tempfile.gettempdir() / "_veriflow_icon.ico"` (reused across sessions)
- Resolve `theme.logo_path()` to absolute using `Path(__file__).parent.parent / logo`
- Silently ignored (`except Exception: pass`) if logo is missing or PIL fails

## Branding rules (mandatory)
- On app startup, load `branding.json` via `ui/theme.py` before any window is created
- Every color used in any UI file must come from `theme.get("key")` — no hardcoded hex values
- Logo loaded once at startup, passed to screens that display it
- If branding.json is missing, theme.py uses built-in defaults silently (no crash, no error shown)
- branding.json lives next to the executable / at project root during development

## Error detector rules (mandatory)
- Build as a pipeline of functions (see SPEC.md Confirmed Decisions section)
- Each check function signature: `def check_name(value: str, dim_values: set, **kwargs) -> dict | None`
- Returns None if no error, returns error dict if error found
- ERROR_CHECKS list at top of error_detector.py controls which checks run
- Adding a new check = add a function + add it to ERROR_CHECKS list. Nothing else changes.

## Section 1 addition
Also create:
- `ui/theme.py` — branding loader
- `branding.json` — default branding file at project root
- `assets/` — empty folder for logo files

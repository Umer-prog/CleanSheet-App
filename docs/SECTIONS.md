# Section Quick Reference

Use this to quickly know what each section builds and what to tell Claude Code.

---

## Section 1 — Project Setup & Data Layer
**Tell Claude Code:**
> "Read SPEC.md and CLAUDE.md. We are building Section 1: Project Setup & Data Layer.
> Build only the files listed for Section 1 in SPEC.md Section 7.
> Start with excel_reader.py and work through the list."

**What gets built:**
- core/ingestion/excel_reader.py
- core/ingestion/file_validator.py
- settings/app_settings.py
- Project folder creation logic (in app_settings.py or a setup.py)
- test_section1.py

**Done when:** You can create a project folder, read an Excel file, save sheets as CSV/JSON, and schema validation blocks a bad re-upload.

---

## Section 2 — Snapshot & History System
**Tell Claude Code:**
> "Read SPEC.md and CLAUDE.md. We are building Section 2: Snapshot & History System.
> Section 1 is already built. Build only Section 2 files."

**What gets built:**
- core/snapshot/snapshot_manager.py
- core/snapshot/orphan_cleaner.py
- test_section2.py

**Done when:** Can hash a CSV, create a snapshot, carry forward unchanged tables, revert to old snapshot, list snapshots.

---

## Section 3 — Mapping Store & Error Engine
**Tell Claude Code:**
> "Read SPEC.md and CLAUDE.md. We are building Section 3: Mapping Store & Error Engine.
> Section 1 is already built. Build only Section 3 files."

**What gets built:**
- core/mapping/mapping_store.py
- core/mapping/mapping_engine.py
- core/mapping/fuzzy_matcher.py
- test_section3.py

**Done when:** Can define a mapping, run error detection, return mismatched values with context.

---

## Section 4 — Screen 0 & Screen 1 (UI)
**Tell Claude Code:**
> "Read SPEC.md and CLAUDE.md. We are building Section 4: Screen 0 and Screen 1 UI.
> Sections 1-3 are already built. Build only Section 4 files.
> UI uses CustomTkinter. No web frameworks."

**What gets built:**
- ui/screen0_launcher.py
- ui/screen1_add_sources.py
- ui/popups/popup_sheet_selector.py
- test_section4.py

**Done when:** App launches, shows project list, can create/open projects, add Excel files, select and categorize sheets.

---

## Section 5 — Screen 2 (UI)
**Tell Claude Code:**
> "Read SPEC.md and CLAUDE.md. We are building Section 5: Screen 2 Mapping Definition UI.
> Sections 1-4 are already built."

**What gets built:**
- ui/screen2_define_mappings.py
- test_section5.py

**Done when:** Can select table pairs, pick join columns, confirm mappings, validate all tables mapped, save to mapping store.

---

## Section 6 — Screen 3 (UI)
**Tell Claude Code:**
> "Read SPEC.md and CLAUDE.md. We are building Section 6: Screen 3 Main Workspace.
> All previous sections are built. This is the final section."

**What gets built:**
- ui/screen3_main_workspace.py
- ui/components/navbar.py
- ui/components/data_table.py
- ui/popups/popup_replace.py
- ui/popups/popup_add_dim_row.py
- ui/popups/popup_history.py
- test_section6.py

**Done when:** Full app works end to end. Navbar switches views. Errors listed. Replace and Add flows work. History popup and revert work.

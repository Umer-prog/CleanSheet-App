# CleanSheet — Performance Optimization Implementation Plan

This document is structured as independent sections. Each section can be handed to a fresh Claude Code session. Complete them in order as some sections have dependencies on earlier ones.

---

## Section 1 — Import Audit (View Only, No Code Changes)

**Objective:** Scan every Python source file in the project and produce a consolidated list of all third-party imports actually used. This list will be used to build a minimal virtual environment for packaging, reducing the final executable size.

**Instructions for Claude Code:**

1. Scan every `.py` file in the project recursively.
2. For each file, collect all `import` and `from ... import` statements.
3. Deduplicate and group by top-level package name (for example, `from PySide6.QtWidgets import QWidget` counts as `PySide6`).
4. Separate the list into two groups:
   - Standard library modules (no installation needed)
   - Third-party packages (need to be in the virtual environment)
5. For PySide6 specifically, list every submodule that is imported anywhere in the codebase (for example `PySide6.QtWidgets`, `PySide6.QtCore`, `PySide6.QtGui`, etc.) so it is known exactly which Qt modules are needed.
6. Write the complete findings into a new file called `IMPORT_AUDIT.md` at the project root. Do not make any changes to any source file. This section is view and document only.

The output file should contain:
- A table of all third-party packages with the specific submodules used
- A separate table of standard library modules used
- A note on any import that looked unused or suspicious (imported but the symbol never referenced in that file)

---

## Section 2 — Parquet Migration with CSV Backward Compatibility

**Objective:** Replace CSV as the internal storage format for transaction and dimension data with Parquet (snappy compression). Existing projects that were saved as CSV must continue to work without any changes from the user.

**Dependencies:** None. This section can be done first or after Section 1.

**Rules:**
- New projects write all tabular data as `.parquet` files with snappy compression.
- When opening an existing project, the app detects whether stored files are `.csv` or `.parquet` by checking file extensions as recorded in the project manifest.
- If a project's manifest references `.csv` files, the app reads them as CSV. No auto-migration happens. The project continues to work exactly as before.
- No prompt, warning, or migration dialog is shown to the user for CSV projects. It is fully transparent.
- A helper function must be created that accepts a file path and returns a DataFrame regardless of whether the file is CSV or Parquet. All read operations across the codebase must go through this helper instead of calling read functions directly.
- A helper function for writing must also be created. It always writes Parquet for new projects. It must not overwrite a CSV path with a Parquet file.
- The project manifest must record the storage format (csv or parquet) when a project is created, so the reader helper knows which format to use without guessing from file extensions alone. If an existing manifest has no format field, the app assumes CSV.
- The final output Excel file is not affected by this change. It remains xlsx.

**Specific areas to update:**
- The function or method responsible for saving transaction data after Screen 1 processing
- The function or method responsible for saving dimension table data
- The function or method responsible for loading data for display in table views
- The function or method responsible for loading data during mapping validation on Screen 3
- The function or method responsible for reading source data when generating the final output file
- The project manifest read and write logic

**Do not change:**
- Any UI code
- Any mapping logic
- The final output file format

---

## Section 3 — Screen 1: Non-blocking File Loading with Progress Feedback

**Objective:** Move all file reading and saving operations that happen after the user confirms their sheet selection on Screen 1 off the main thread. The UI must remain responsive. A progress indicator must be shown while work is in progress.

**Dependencies:** Section 2 must be complete, as workers will use the new write helpers.

**What to implement:**

Create a QThread worker class responsible for the following steps, in order, for each sheet the user added:
1. Read the source Excel file for that sheet using pandas
2. Save the resulting DataFrame using the write helper from Section 2
3. Emit a signal after each sheet is processed so the UI can update a progress indicator

The worker must emit the following signals:
- A progress signal carrying the count of sheets completed so far and the total count
- A completion signal carrying any data the main thread needs to continue navigation
- An error signal carrying a description if any sheet fails to load

On the main thread:
- Show a progress bar or progress label in the UI while the worker is running
- The Next or Confirm button must be disabled until the worker emits its completion signal
- On error, show the error to the user and allow them to retry or go back
- Do not navigate away from Screen 1 until the worker signals completion

Additionally, use a ThreadPoolExecutor inside the worker's run method to read multiple Excel files concurrently. The writes must still happen sequentially after each read completes to avoid file system conflicts. The number of concurrent read threads should be capped at 4.

---

## Section 4 — Screen 3: Cached Validation with Non-blocking Recalculation

**Objective:** Eliminate the freeze when navigating to Screen 3 by caching validation results and only recalculating when data has actually changed.

**Dependencies:** Section 2 must be complete.

**Two parts to implement:**

**Part A — Dirty flag and cache:**

Introduce a session-level flag called `mappings_dirty`. This flag starts as True when a project is first opened or when any of the following actions occur:
- A mapping is added or removed
- A source file is re-uploaded
- A dimension table is replaced

When the user navigates to Screen 3 and `mappings_dirty` is False, load the cached validation result from the last calculation and display it immediately. Do not recalculate.

The cached result must be stored in memory (a dictionary or dataclass on the project session object) and must include everything Screen 3 needs to render: error counts, affected row identifiers, and per-column summaries. The cache does not need to be persisted to disk between app sessions.

**Part B — Background validation worker:**

When `mappings_dirty` is True, Screen 3 must not block the main thread while calculating. Implement a QThread worker that performs the validation logic. The worker emits a completion signal carrying the result dictionary. While the worker runs, Screen 3 shows a loading state (a spinner or placeholder text) in the content area. The navigation sidebar remains fully interactive — the user can navigate away, which must cancel or abandon the worker cleanly.

On completion, the main thread stores the result in the cache, sets `mappings_dirty` to False, and renders the results.

---

## Section 5 — Dimension Table Search: Debounce and Background Filter

**Objective:** Fix the freeze when searching in the dimension table view for larger tables.

**Dependencies:** Section 2 must be complete (search operates on the loaded DataFrame).

**Three changes to make:**

**Change A — Debounce the search input:**

The search input must not trigger filtering on every keystroke. Use a QTimer set to 300 milliseconds. Each keystroke resets the timer. Filtering only fires when the timer completes, meaning the user has paused typing for 300ms.

**Change B — Vectorized filter logic:**

Replace any row-wise apply or iteration-based search with the following approach: for each column in the DataFrame, convert the column to string type and check whether each value contains the search query (case-insensitive). Combine the per-column boolean masks with a logical OR to produce a single mask, then use that mask to filter the DataFrame. This must replace whatever the current implementation uses.

**Change C — Background filter worker:**

Move the filter operation into a QThread worker. The worker accepts the full DataFrame and the search query, performs the vectorized filter, and emits the filtered DataFrame via a signal. The main thread then updates the table model with the result. While filtering, the table view can remain showing the previous results or show a subtle loading indicator. Do not block the main thread.

---

## Section 6 — Final File Generation: Non-blocking Export

**Objective:** Move final Excel file generation off the main thread and switch to the xlsxwriter engine for faster writes.

**Dependencies:** Section 2 must be complete, as generation reads from Parquet or CSV via the read helper.

**What to implement:**

Create a QThread worker for the export process. The worker must:
1. Read all required source DataFrames using the read helper from Section 2
2. Apply all mappings to produce the output DataFrame
3. Write the output file as xlsx using the xlsxwriter engine (pass `engine='xlsxwriter'` to the pandas Excel writer)
4. Emit a progress signal at meaningful steps (reading done, mappings applied, writing done)
5. Emit a completion signal with the output file path on success
6. Emit an error signal with a description on failure

On the main thread:
- Show a progress dialog or progress bar when export starts
- Disable the export button while the worker runs
- On completion, show a success message and allow the user to open the file location
- On error, show the error and allow retry

Do not change the output file format or the Excel formatting that is currently applied. Only the threading and engine change.

---

## Section 7 — PyInstaller Build: Minimal Environment

**Objective:** Reduce the packaged executable size by building from a clean, minimal virtual environment and excluding unused modules.

**Dependencies:** Section 1 (IMPORT_AUDIT.md) must be complete, as the package list from that audit drives what gets installed.

**Instructions for Claude Code:**

1. Read IMPORT_AUDIT.md to get the confirmed list of third-party packages the app actually uses.
2. Update or create the PyInstaller spec file to add explicit excludes for modules that are confirmed unused. Candidates to exclude unless found in the audit include: `tkinter`, `unittest`, `http.server`, `email`, `xml.etree`, `multiprocessing` (if unused), `sqlite3` (if unused), `distutils`, `test`, `lib2to3`.
3. If the current build uses the full `PySide6` package, switch the spec to use only the Qt submodules confirmed in the audit. Add only those submodules to `hiddenimports`.
4. Add UPX compression to the spec if not already present.
5. Do not modify any application source file. Only the spec file and the documented build instructions change.
6. Update or create the build command file to reflect the new spec, and note that the build must be run from a virtual environment that contains only the packages listed in IMPORT_AUDIT.md.

---

## Notes for All Sessions

- The read/write helpers introduced in Section 2 are the single point of change for storage format. All other sections reference them but do not re-implement storage logic.
- QThread workers follow the same pattern throughout: subclass QThread, override run(), emit signals, connect signals to main-thread slots. No direct UI manipulation from within a worker.
- The CSV backward compatibility guarantee applies to all sections. If a test project saved as CSV is opened at any point, it must continue to load and display correctly.
- The final output file is always xlsx. No section changes this.
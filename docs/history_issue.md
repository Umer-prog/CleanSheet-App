# Requirements: Metadata Pointers & Improved Commit Structure

## Overview

Two focused changes to the existing history system:

1. Move the live `data/` and `mappings/` folders into a `metadata/` folder, and make them work as pointers to the currently active commit in the `history/` folder
2. Improve the commit structure inside `history/` so each commit saves all required data in separate subfolders

---

## Change 1: Metadata Folder with Pointers

### Current structure

```
<workspace_root>/
├── data/
├── final/
├── history/
├── mappings/
├── project.json
└── settings.json
```

### Required structure

```
<workspace_root>/
├── metadata/
│   ├── data/
│   └── mappings/
├── history/
├── project.json
└── settings.json
```

The `data/` and `mappings/` folders are moved inside a new `metadata/` folder. Nothing else about their content changes at this stage — the move is structural.

### How the pointers work

`metadata/data/` and `metadata/mappings/` stop being the source of truth for project state. Instead, they become pointers — they hold a reference to whichever commit ID is currently active in the `history/` folder.

When the application needs to read transaction data, dimension data, or mappings, it:

1. Reads the current commit ID from the pointer in `metadata/`
2. Goes to `history/<commit_id>/` and reads from the appropriate subfolder there

When the user moves to a different commit (revert or history navigation):

1. The pointer in `metadata/` is updated to the new commit ID
2. The application reads from `history/<new_commit_id>/`
3. All views are re-rendered from that commit's data

No data is copied when moving between commits. Only the pointer changes.

---

## Change 2: Improved Commit Structure in History Folder

### Current commit structure

Each commit in `history/` currently saves some data but not in a complete, consistently separated way.

### Required commit structure

Each commit folder inside `history/` must save all required project data in clearly separated subfolders:

```
history/
└── <commit_id>/
    ├── commit.json         ← commit metadata (id, timestamp, label, parent)
    ├── transactions/       ← all transaction table CSVs for this commit
    ├── dimensions/         ← all dimension table CSVs and their JSON metadata
    ├── mappings/           ← mapping registry JSON for this commit
    └── ignored/            ← ignored rows data for this commit
```

Every commit must contain all four subfolders. When the metadata pointer moves to a commit, the application has everything it needs in one place — transaction data, dimension data, mappings, and ignored rows — without looking anywhere else.

### Why this matters

When the pointer in `metadata/` changes to a different commit ID, the application simply reads from that commit's subfolders and re-renders. Because every commit is self-contained, the rendered state is exactly what it was when that commit was saved — data, mappings, and ignored rows all match.

---

## Behaviour Unchanged

- Commit IDs and how they are generated remain the same
- The maximum commit limit and pruning logic remain the same
- The initial commit flow remains the same
- The `project.json` and `settings.json` files stay at the workspace root, outside `metadata/`


but for fist setup it can make csv and json in side metadata/data/
and jason for mapping in metadata/mappings/
but then later after first setup it should just use pointers in it. and u must not delete or refrence these first initial setup phase files.
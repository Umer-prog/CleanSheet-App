# /start-section command
# Usage: /start-section 1
# Tells Claude Code which section to work on and what context to load

Read SPEC.md fully before writing any code.
Then read CLAUDE.md for coding rules.

The section to build is specified in the argument.

For the requested section:
1. List exactly which files need to be created (from SPEC.md Section 7)
2. Confirm which sections it depends on and check those files exist
3. Ask if anything is unclear before writing code
4. Build each file one at a time, showing the complete file before moving on
5. After all files are built, create test_section{N}.py and verify it runs

# Command: add-feature
# Usage: /add-feature <description>
# Adds a feature that is not in the current section plan

Read CLAUDE.md and docs/SPEC.md first.
The user wants to add: $ARGUMENTS

Before implementing:
1. Identify which existing files this touches
2. Confirm it does not break any existing section's logic
3. Check if it needs a new manager method or just a UI change
4. Implement it following all rules in CLAUDE.md
5. Update docs/SPEC.md to document the new feature at the bottom under "Added Features"

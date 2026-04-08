# /review-section command
# Usage: /review-section 2
# Reviews built section against the spec for correctness

Read SPEC.md Section 7 for what this section should have built.
Then read each file that was built for this section.

Check:
1. All listed files exist
2. Every function has a docstring
3. No hardcoded paths (pathlib.Path used everywhere)
4. All file operations have try/except
5. No function exceeds 50 lines
6. All string comparisons use .strip().lower()
7. Behaviour matches what SPEC.md describes for this section

Report: what passes, what needs fixing, what is missing.

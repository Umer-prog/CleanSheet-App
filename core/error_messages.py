"""Converts raw exceptions into plain-English user-facing messages.

Rules:
- Never expose a Python class name or internal traceback detail.
- Always include a suggestion of what the user can do.
- Keep it short — one or two sentences max.
"""
from __future__ import annotations


def friendly_error(exc: BaseException) -> str:
    """Return a plain-English, actionable message for any exception.

    Callers (UI layers) pass the raw exception here instead of str(exc).
    The result is safe to display directly in a dialog or error label.
    """
    msg = str(exc).lower()

    # --- File-locking (Excel open in another program) ---
    if isinstance(exc, PermissionError) or "permission denied" in msg:
        return (
            "The file is locked by another program (e.g. Excel).\n"
            "Close the file and try again."
        )

    # --- Disk full ---
    if isinstance(exc, OSError) and (
        getattr(exc, "errno", None) == 28          # ENOSPC Linux/Mac
        or getattr(exc, "winerror", None) == 112   # ERROR_DISK_FULL Windows
        or "no space left" in msg
        or "disk full" in msg
        or "there is not enough space" in msg
    ):
        return (
            "There is not enough disk space to complete this operation.\n"
            "Free up space and try again."
        )

    # --- Corrupted file (bad zip / bad parquet) ---
    if "bad zip" in msg or "not a zip" in msg or "badzip" in msg:
        return (
            "The file appears to be corrupted and cannot be opened.\n"
            "Try re-exporting the file from its source."
        )

    # --- Password-protected Excel ---
    if "password" in msg or "encrypt" in msg or "protected" in msg:
        return (
            "The file is password-protected and cannot be opened.\n"
            "Remove the password in Excel and try again."
        )

    # --- Parquet schema mismatch ---
    if "schema" in msg or "arrowinvalid" in msg or "parquet" in msg and "mismatch" in msg:
        return (
            "The data file has an unexpected format.\n"
            "The project may need to be re-imported."
        )

    # --- File not found ---
    if isinstance(exc, FileNotFoundError) or "not found" in msg or "no such file" in msg:
        return "The file could not be found. It may have been moved or deleted."

    # --- Generic value / type errors (hide class names) ---
    if isinstance(exc, (ValueError, TypeError)):
        # Strip leading class-name prefix if present (e.g. "ValueError: ...")
        text = str(exc)
        for prefix in ("ValueError:", "TypeError:", "KeyError:", "IndexError:"):
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
        return text or "An unexpected error occurred."

    # --- Fallback: return the message but strip the class-name prefix ---
    text = str(exc)
    # "SomeException: actual message" → "actual message"
    if ":" in text:
        after_colon = text.split(":", 1)[1].strip()
        if after_colon:
            return after_colon

    return text or "An unexpected error occurred."

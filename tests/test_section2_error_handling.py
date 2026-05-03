"""Tests for Section 2 — Error Handling improvements."""
from __future__ import annotations

import json
import struct
import tempfile
from pathlib import Path

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_project(tmp_path: Path, fmt: str = "parquet") -> Path:
    """Create a minimal project structure for testing."""
    from core.project_paths import internal_path
    project_path = tmp_path / "TestProject"
    ip = internal_path(project_path)
    for sub in ["metadata/data/transactions", "metadata/data/dim", "metadata/mappings"]:
        (ip / sub).mkdir(parents=True, exist_ok=True)
    (ip / "project.json").write_text(
        json.dumps({"project_name": "TestProject", "storage_format": fmt}),
        encoding="utf-8",
    )
    (ip / "settings.json").write_text(
        json.dumps({"history_enabled": True, "current_manifest": None}),
        encoding="utf-8",
    )
    return project_path


# ---------------------------------------------------------------------------
# friendly_error()
# ---------------------------------------------------------------------------

class TestFriendlyError:
    def test_permission_error_message(self):
        from core.error_messages import friendly_error
        msg = friendly_error(PermissionError("Access is denied"))
        assert "open in another program" in msg.lower() or "locked" in msg.lower()
        assert "try again" in msg.lower()

    def test_disk_full_winerror(self):
        from core.error_messages import friendly_error
        exc = OSError("Not enough space")
        exc.winerror = 112
        msg = friendly_error(exc)
        assert "disk space" in msg.lower()
        assert "free" in msg.lower()

    def test_bad_zip_corrupted(self):
        from core.error_messages import friendly_error
        msg = friendly_error(Exception("File is not a zip file"))
        assert "corrupt" in msg.lower()

    def test_password_protected(self):
        from core.error_messages import friendly_error
        msg = friendly_error(Exception("File is password protected"))
        assert "password" in msg.lower()

    def test_file_not_found(self):
        from core.error_messages import friendly_error
        msg = friendly_error(FileNotFoundError("No such file or directory: 'x.csv'"))
        assert "not found" in msg.lower() or "moved or deleted" in msg.lower()

    def test_strips_class_name_prefix(self):
        from core.error_messages import friendly_error
        msg = friendly_error(ValueError("ValueError: bad input"))
        # Should not start with "ValueError:"
        assert not msg.startswith("ValueError:")

    def test_generic_exception_strips_colon_prefix(self):
        from core.error_messages import friendly_error
        msg = friendly_error(RuntimeError("RuntimeError: something went wrong"))
        assert "something went wrong" in msg

    def test_empty_exception_returns_fallback(self):
        from core.error_messages import friendly_error
        msg = friendly_error(Exception(""))
        assert msg  # not empty


# ---------------------------------------------------------------------------
# data_loader — Excel PermissionError
# ---------------------------------------------------------------------------

class TestExcelPermissionError:
    def test_load_excel_sheets_permission_raises_cleanly(self, tmp_path):
        """PermissionError from a locked file becomes a PermissionError with a helpful message."""
        from unittest.mock import patch
        from core.data_loader import load_excel_sheets

        fake_xlsx = tmp_path / "locked.xlsx"
        fake_xlsx.write_bytes(b"dummy")

        with patch("pandas.ExcelFile", side_effect=PermissionError("Access denied")):
            with pytest.raises(PermissionError) as exc_info:
                load_excel_sheets(fake_xlsx)

        msg = str(exc_info.value).lower()
        assert "open in another program" in msg or "close" in msg

    def test_load_excel_sheets_bad_zip_raises_with_hint(self, tmp_path):
        """Corrupted file raises ValueError with a clear message."""
        from unittest.mock import patch
        from core.data_loader import load_excel_sheets

        fake_xlsx = tmp_path / "corrupt.xlsx"
        fake_xlsx.write_bytes(b"not a zip")

        with patch("pandas.ExcelFile", side_effect=Exception("File is not a zip file")):
            with pytest.raises(ValueError) as exc_info:
                load_excel_sheets(fake_xlsx)

        assert "corrupt" in str(exc_info.value).lower()

    def test_load_excel_sheets_password_raises_with_hint(self, tmp_path):
        """Password-protected file raises ValueError with a clear message."""
        from unittest.mock import patch
        from core.data_loader import load_excel_sheets

        fake_xlsx = tmp_path / "protected.xlsx"
        fake_xlsx.write_bytes(b"dummy")

        with patch("pandas.ExcelFile", side_effect=Exception("File is password protected")):
            with pytest.raises(ValueError) as exc_info:
                load_excel_sheets(fake_xlsx)

        assert "password" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# data_loader — Parquet schema mismatch
# ---------------------------------------------------------------------------

class TestParquetErrors:
    def test_read_table_schema_mismatch_raises_clearly(self, tmp_path):
        """A corrupted / schema-mismatched parquet raises a clear ValueError."""
        from unittest.mock import patch
        from core.data_loader import read_table

        bad_parquet = tmp_path / "bad.parquet"
        bad_parquet.write_bytes(b"not real parquet data")

        # pyarrow raises ArrowInvalid on bad parquet; simulate with Exception containing "invalid"
        with patch("pandas.read_parquet", side_effect=Exception("ArrowInvalid: schema mismatch")):
            with pytest.raises((ValueError, OSError)) as exc_info:
                read_table(bad_parquet)

        msg = str(exc_info.value).lower()
        assert "format" in msg or "schema" in msg or "re-imported" in msg

    def test_write_table_disk_full_winerror(self, tmp_path):
        """Disk-full WinError 112 from to_parquet raises a clean OSError."""
        from unittest.mock import patch
        from core.data_loader import write_table

        dest = tmp_path / "output.parquet"
        df = pd.DataFrame({"a": ["1", "2"]})

        disk_full = OSError("No space left")
        disk_full.winerror = 112

        with patch("pandas.DataFrame.to_parquet", side_effect=disk_full):
            with pytest.raises(OSError) as exc_info:
                write_table(df, dest)

        msg = str(exc_info.value).lower()
        assert "disk space" in msg or "space" in msg

    def test_write_table_disk_full_errno28(self, tmp_path):
        """Disk-full errno 28 from to_csv raises a clean OSError."""
        from unittest.mock import patch
        from core.data_loader import write_table

        dest = tmp_path / "output.csv"
        df = pd.DataFrame({"a": ["1", "2"]})

        disk_full = OSError("No space left on device")
        disk_full.errno = 28

        with patch("pandas.DataFrame.to_csv", side_effect=disk_full):
            with pytest.raises(OSError) as exc_info:
                write_table(df, dest)

        msg = str(exc_info.value).lower()
        assert "disk space" in msg or "space" in msg


# ---------------------------------------------------------------------------
# msgbox — critical_with_log exists and is callable
# ---------------------------------------------------------------------------

pyside6_available = pytest.importorskip  # used below


class TestCriticalWithLog:
    def test_function_exists(self):
        pytest.importorskip("PySide6")
        from ui.popups.msgbox import critical_with_log
        assert callable(critical_with_log)

    def test_get_log_file_path_returns_path_after_setup(self):
        from core.app_logger import setup_logging, get_log_file_path
        setup_logging()
        p = get_log_file_path()
        assert p is not None
        assert p.suffix == ".log"

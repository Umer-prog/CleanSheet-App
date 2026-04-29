"""
Section 8 — Data Integrity tests.

Covers:
  - Atomic writes: no partial destination file on failure; destination only
    updated after a successful write.
  - Read-back row-count validation for Parquet.
  - CSV atomic path exercised (successful write).
  - Temp file cleaned up on failure.
  - Existing CSV blocks Parquet write (format protection).
  - Original source file never modified.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from core.data_loader import write_table, read_table


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_df(rows: int = 5) -> pd.DataFrame:
    return pd.DataFrame(
        {"id": [str(i) for i in range(rows)], "value": [f"v{i}" for i in range(rows)]}
    )


# ---------------------------------------------------------------------------
# 1. Atomic writes — Parquet
# ---------------------------------------------------------------------------

class TestAtomicParquet:
    def test_writes_to_destination_not_tmp(self, tmp_path):
        dest = tmp_path / "data.parquet"
        write_table(_sample_df(), dest)
        assert dest.exists()
        assert not dest.with_suffix(".parquet.tmp").exists()

    def test_no_partial_file_on_write_error(self, tmp_path):
        """If to_parquet raises, destination must remain untouched."""
        dest = tmp_path / "data.parquet"
        # Write a valid initial file so we can verify it's unchanged
        original_df = _sample_df(3)
        write_table(original_df, dest)
        original_mtime = dest.stat().st_mtime

        with patch("pandas.DataFrame.to_parquet", side_effect=OSError("disk failure")):
            with pytest.raises(OSError):
                write_table(_sample_df(5), dest)

        # Destination unchanged
        assert dest.stat().st_mtime == original_mtime
        # Temp file cleaned up
        assert not dest.with_suffix(".parquet.tmp").exists()

    def test_no_destination_created_when_write_fails_fresh(self, tmp_path):
        """On failure with no pre-existing destination, destination must not be created."""
        dest = tmp_path / "new.parquet"
        with patch("pandas.DataFrame.to_parquet", side_effect=OSError("disk failure")):
            with pytest.raises(OSError):
                write_table(_sample_df(), dest)

        assert not dest.exists()
        assert not dest.with_suffix(".parquet.tmp").exists()

    def test_destination_updated_on_success(self, tmp_path):
        dest = tmp_path / "data.parquet"
        write_table(_sample_df(3), dest)
        write_table(_sample_df(7), dest)
        result = read_table(dest)
        assert len(result) == 7


# ---------------------------------------------------------------------------
# 2. Post-write read-back validation — Parquet
# ---------------------------------------------------------------------------

class TestParquetReadback:
    def test_raises_on_row_count_mismatch(self, tmp_path):
        """Simulate silent corruption: write succeeds but read-back returns fewer rows."""
        dest = tmp_path / "data.parquet"
        df_small = _sample_df(2)

        # Make pd.read_parquet return a shorter frame than what was written
        real_read = pd.read_parquet
        call_count = {"n": 0}

        def fake_read(path, *args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return df_small  # simulates truncated read-back
            return real_read(path, *args, **kwargs)

        with patch("pandas.read_parquet", side_effect=fake_read):
            with pytest.raises(OSError, match="validation failed"):
                write_table(_sample_df(5), dest)

        # Temp file must be cleaned up
        assert not dest.with_suffix(".parquet.tmp").exists()

    def test_passes_on_correct_row_count(self, tmp_path):
        dest = tmp_path / "data.parquet"
        df = _sample_df(10)
        returned = write_table(df, dest)
        assert returned == dest
        assert len(read_table(dest)) == 10


# ---------------------------------------------------------------------------
# 3. Atomic writes — CSV
# ---------------------------------------------------------------------------

class TestAtomicCSV:
    def test_writes_to_destination_not_tmp(self, tmp_path):
        dest = tmp_path / "data.csv"
        write_table(_sample_df(), dest)
        assert dest.exists()
        assert not Path(str(dest) + ".tmp").exists()

    def test_no_partial_file_on_write_error(self, tmp_path):
        dest = tmp_path / "data.csv"
        original_df = _sample_df(3)
        write_table(original_df, dest)
        original_mtime = dest.stat().st_mtime

        with patch("pandas.DataFrame.to_csv", side_effect=OSError("disk failure")):
            with pytest.raises(OSError):
                write_table(_sample_df(5), dest)

        assert dest.stat().st_mtime == original_mtime
        assert not Path(str(dest) + ".tmp").exists()

    def test_destination_updated_on_success(self, tmp_path):
        dest = tmp_path / "data.csv"
        write_table(_sample_df(2), dest)
        write_table(_sample_df(8), dest)
        result = read_table(dest)
        assert len(result) == 8


# ---------------------------------------------------------------------------
# 4. Format protection — CSV blocks Parquet
# ---------------------------------------------------------------------------

class TestFormatProtection:
    def test_parquet_write_blocked_when_csv_exists(self, tmp_path):
        csv_path = tmp_path / "data.csv"
        write_table(_sample_df(), csv_path)

        parquet_path = tmp_path / "data.parquet"
        with pytest.raises(FileExistsError, match="CSV file already exists"):
            write_table(_sample_df(), parquet_path)

        assert not parquet_path.exists()


# ---------------------------------------------------------------------------
# 5. Source file never modified
# ---------------------------------------------------------------------------

class TestSourceFileImmutability:
    def test_source_file_not_touched(self, tmp_path):
        """The source file mtime must not change after write_table writes elsewhere."""
        src = tmp_path / "source.parquet"
        original_df = _sample_df(4)
        # Write source directly (bypassing write_table to get a known mtime)
        original_df.to_parquet(src, index=False)
        mtime_before = src.stat().st_mtime

        dest = tmp_path / "copy.parquet"
        write_table(original_df, dest)

        assert src.stat().st_mtime == mtime_before


# ---------------------------------------------------------------------------
# 6. Disk-full error surfaced with plain-English message
# ---------------------------------------------------------------------------

class TestDiskFullMessages:
    def test_parquet_disk_full_message(self, tmp_path):
        dest = tmp_path / "data.parquet"
        err = OSError("No space left")
        err.errno = 28
        with patch("pandas.DataFrame.to_parquet", side_effect=err):
            with pytest.raises(OSError, match="Not enough disk space"):
                write_table(_sample_df(), dest)

    def test_csv_disk_full_message(self, tmp_path):
        dest = tmp_path / "data.csv"
        err = OSError("No space left")
        err.errno = 28
        with patch("pandas.DataFrame.to_csv", side_effect=err):
            with pytest.raises(OSError, match="Not enough disk space"):
                write_table(_sample_df(), dest)

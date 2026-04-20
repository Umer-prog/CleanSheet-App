import json
import re
from datetime import date, datetime
from pathlib import Path

import pandas as pd


def _excel_numfmt_to_strftime(number_format: str) -> str | None:
    """Convert an Excel number format string to a Python strftime string.

    Returns None if the format doesn't contain date tokens.
    """
    fmt = (number_format or "").strip()
    # Strip color codes e.g. [Red], [Black]
    fmt = re.sub(r'\[[^\]]+\]', '', fmt)
    # Strip quoted literal text e.g. "dd \"of\" mmm"
    fmt = re.sub(r'"[^"]*"', '', fmt)

    # Must contain at least one unambiguous date/year token to qualify
    if not re.search(r'y{1,4}|d{1,4}|mmm', fmt, re.IGNORECASE):
        return None

    result = fmt
    # Replace tokens longest-first to avoid partial matches
    result = re.sub(r'(?i)yyyy', '%Y', result)
    result = re.sub(r'(?i)yy',   '%y', result)
    result = re.sub(r'(?i)mmmm', '%B', result)
    result = re.sub(r'(?i)mmm',  '%b', result)
    result = re.sub(r'(?i)mm',   '%m', result)
    result = re.sub(r'(?i)m',    '%m', result)
    result = re.sub(r'(?i)dddd', '%A', result)
    result = re.sub(r'(?i)ddd',  '%a', result)
    result = re.sub(r'(?i)dd',   '%d', result)
    result = re.sub(r'(?i)d',    '%d', result)
    result = re.sub(r'(?i)hh',   '%H', result)
    result = re.sub(r'(?i)h',    '%H', result)
    result = re.sub(r'(?i)ss',   '%S', result)

    return result if '%' in result else None


def load_excel_sheets(file_path: Path) -> list:
    """Return the list of sheet names in an Excel file."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Excel file not found: {file_path}")
    try:
        xl = pd.ExcelFile(file_path, engine="openpyxl")
        return xl.sheet_names
    except Exception as e:
        raise ValueError(f"Failed to open Excel file '{file_path}': {e}") from e


def get_sheet_as_dataframe(file_path: Path, sheet_name: str) -> pd.DataFrame:
    """Read a single sheet from an Excel file and return a DataFrame.

    Date/time cells are formatted as strings that match their original Excel
    display format (e.g. dd/mm/yyyy), so the value round-trips correctly
    through CSV and back into the final output workbook.
    """
    import openpyxl

    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Excel file not found: {file_path}")
    try:
        wb = openpyxl.load_workbook(str(file_path), data_only=True)
        if sheet_name not in wb.sheetnames:
            raise ValueError(f"Sheet '{sheet_name}' not found in '{file_path}'")
        ws = wb[sheet_name]

        if not ws.max_row:
            wb.close()
            return pd.DataFrame()

        # --- headers (row 1) ---
        headers = [
            str(cell.value).strip() if cell.value is not None else f"Col{i}"
            for i, cell in enumerate(ws[1], start=1)
        ]

        # --- detect per-column strftime format from first ~20 data rows ---
        col_strftime: dict[int, str] = {}   # 0-based column index → strftime
        scan_end = min(ws.max_row, 21)
        for ci in range(len(headers)):
            for row_cells in ws.iter_rows(min_row=2, max_row=scan_end,
                                          min_col=ci + 1, max_col=ci + 1):
                for cell in row_cells:
                    if cell.value is not None and isinstance(cell.value, (date, datetime)):
                        fmt = _excel_numfmt_to_strftime(cell.number_format or "")
                        if fmt:
                            col_strftime[ci] = fmt
                        break
                if ci in col_strftime:
                    break

        # --- build data rows ---
        data_rows = []
        for row_cells in ws.iter_rows(min_row=2, values_only=False):
            row_data = []
            for ci in range(len(headers)):
                cell = row_cells[ci] if ci < len(row_cells) else None
                val = cell.value if cell is not None else None

                if val is None:
                    row_data.append("")
                elif ci in col_strftime and isinstance(val, (date, datetime)):
                    try:
                        row_data.append(val.strftime(col_strftime[ci]))
                    except Exception:
                        row_data.append(str(val))
                else:
                    row_data.append(str(val))
            data_rows.append(row_data)

        wb.close()
        df = pd.DataFrame(data_rows, columns=headers)
        return df

    except (FileNotFoundError, ValueError):
        raise
    except Exception as e:
        raise ValueError(f"Failed to read sheet '{sheet_name}' from '{file_path}': {e}") from e


def save_as_csv(df: pd.DataFrame, dest_path: Path) -> None:
    """Save a DataFrame as a CSV file."""
    dest_path = Path(dest_path)
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(dest_path, index=False, encoding="utf-8")
    except OSError as e:
        raise OSError(f"Failed to save CSV to '{dest_path}': {e}") from e


def save_as_json(df: pd.DataFrame, dest_path: Path) -> None:
    """Save a DataFrame as a JSON file (records format, one object per row)."""
    dest_path = Path(dest_path)
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        records = df.to_dict(orient="records")
        with open(dest_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
    except OSError as e:
        raise OSError(f"Failed to save JSON to '{dest_path}': {e}") from e


def load_csv(file_path: Path) -> pd.DataFrame:
    """Load a CSV file as a DataFrame (all columns as strings)."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")
    try:
        return pd.read_csv(file_path, dtype=str, encoding="utf-8")
    except Exception as e:
        raise ValueError(f"Failed to load CSV '{file_path}': {e}") from e


def load_dim_json(file_path: Path) -> pd.DataFrame:
    """Load a dim JSON file (records list) as a DataFrame."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Dim JSON file not found: {file_path}")
    try:
        with open(file_path, encoding="utf-8") as f:
            records = json.load(f)
        return pd.DataFrame(records).astype(str)
    except Exception as e:
        raise ValueError(f"Failed to load dim JSON '{file_path}': {e}") from e

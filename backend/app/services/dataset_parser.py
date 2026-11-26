"""
Dataset Loader & Parser Service
Supports ingestion of participant data from:
- Modern Excel Spreadsheets (.xlsx, .xlsm, .xltx) via openpyxl
- Legacy Excel Spreadsheets (.xls) via xlrd
- Delimited Spreadsheets (.csv, .tsv) via standard csv module
- JSON files (.json) via standard json module

Provides header sanitization, type coercion (dates, integers, floats),
and row-level validation.
"""

import io
import os
import re
import csv
import json
import datetime
from typing import List, Dict, Any, Union, Optional

import openpyxl
import xlrd


def _coerce_cell_value(val: Any) -> str:
    """Converts cell values (numbers, dates, booleans) to clean normalized strings."""
    if val is None:
        return ""
    if isinstance(val, (datetime.date, datetime.datetime)):
        return val.strftime("%Y-%m-%d") if isinstance(val, datetime.date) else val.isoformat()
    if isinstance(val, float):
        # Format whole numbers cleanly (e.g. 1001.0 -> "1001")
        if val.is_integer():
            return str(int(val))
        return str(val)
    if isinstance(val, int):
        return str(val)
    if isinstance(val, bool):
        return "true" if val else "false"
    return re.sub(r"\s+", " ", str(val)).strip()


def parse_xlsx_bytes(content: bytes) -> List[Dict[str, Any]]:
    """Parses an Excel .xlsx workbook from bytes."""
    wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True, read_only=True)
    sheet = wb.active
    rows = list(sheet.iter_rows(values_only=True))
    wb.close()
    return _parse_raw_rows(rows)


def parse_xls_bytes(content: bytes) -> List[Dict[str, Any]]:
    """Parses a legacy Excel .xls workbook from bytes."""
    book = xlrd.open_workbook(file_contents=content)
    sheet = book.sheet_by_index(0)
    rows = []
    for r in range(sheet.nrows):
        row_vals = []
        for c in range(sheet.ncols):
            cell_type = sheet.cell_type(r, c)
            val = sheet.cell_value(r, c)
            if cell_type == xlrd.XL_CELL_DATE:
                try:
                    dt_tuple = xlrd.xldate_as_tuple(val, book.datemode)
                    val = datetime.date(dt_tuple[0], dt_tuple[1], dt_tuple[2]).strftime("%Y-%m-%d")
                except Exception:
                    val = str(val)
            row_vals.append(val)
        rows.append(row_vals)
    return _parse_raw_rows(rows)


def parse_csv_bytes(content: bytes) -> List[Dict[str, Any]]:
    """Parses CSV/TSV content from bytes with automatic dialect detection."""
    # Try decoding as utf-8, fallback to latin-1
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    # Detect delimiter (comma vs tab vs semicolon)
    sample = text[:4096]
    delimiter = ","
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
        delimiter = dialect.delimiter
    except Exception:
        if "\t" in sample and sample.count("\t") > sample.count(","):
            delimiter = "\t"
        elif ";" in sample and sample.count(";") > sample.count(","):
            delimiter = ";"

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)
    return _parse_raw_rows(rows)


def parse_json_bytes(content: bytes) -> List[Dict[str, Any]]:
    """Parses JSON participant data from bytes."""
    try:
        data = json.loads(content.decode("utf-8-sig"))
    except UnicodeDecodeError:
        data = json.loads(content.decode("latin-1"))

    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    elif isinstance(data, dict):
        # Look for keys like 'participants', 'records', 'data', 'items'
        for key in ("participants", "records", "data", "items"):
            if key in data and isinstance(data[key], list):
                return [r for r in data[key] if isinstance(r, dict)]
        return [data]
    return []


def _parse_raw_rows(rows: List[Any]) -> List[Dict[str, Any]]:
    """Converts a 2D list of row values into a list of dict records."""
    if not rows:
        return []

    # Find the first real header row (skipping single-cell title/banner rows when multi-column data exists)
    header_idx = -1
    headers: List[str] = []
    first_non_empty_idx = -1
    first_non_empty_headers: List[str] = []
    for idx, row in enumerate(rows):
        cleaned = [_coerce_cell_value(c) for c in (row or [])]
        non_empty_count = sum(1 for c in cleaned if c)
        if non_empty_count > 0 and first_non_empty_idx == -1:
            first_non_empty_idx = idx
            first_non_empty_headers = cleaned
        if non_empty_count >= 2:
            headers = cleaned
            header_idx = idx
            break

    if header_idx == -1 and first_non_empty_idx != -1:
        header_idx = first_non_empty_idx
        headers = first_non_empty_headers

    if header_idx == -1 or not headers:
        return []

    records: List[Dict[str, Any]] = []
    for row in rows[header_idx + 1:]:
        if not row:
            continue
        vals = [_coerce_cell_value(c) for c in row]
        # Ignore completely empty rows
        if not any(vals):
            continue

        record: Dict[str, Any] = {}
        for h, v in zip(headers, vals):
            h_clean = h.strip()
            if h_clean:
                record[h_clean] = v
        if record:
            records.append(record)

    return records


def load_dataset(
    file_path: Optional[str] = None,
    content_bytes: Optional[bytes] = None,
    filename: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Unified dataset ingestion function.
    Can read from a file path or from in-memory content bytes and filename.
    Supports .xlsx, .xlsm, .xltx, .xls, .csv, .tsv, .json.
    """
    if file_path:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Dataset file not found: {file_path}")
        filename = filename or os.path.basename(file_path)
        with open(file_path, "rb") as f:
            content_bytes = f.read()

    if not content_bytes:
        raise ValueError("No dataset content provided or file is empty.")

    ext = (filename or "").lower().split(".")[-1]

    if ext in ("xlsx", "xlsm", "xltx"):
        return parse_xlsx_bytes(content_bytes)
    elif ext == "xls":
        return parse_xls_bytes(content_bytes)
    elif ext in ("csv", "tsv", "txt"):
        return parse_csv_bytes(content_bytes)
    elif ext == "json":
        return parse_json_bytes(content_bytes)
    else:
        # Fallback heuristic: try JSON, then CSV, then XLSX
        try:
            return parse_json_bytes(content_bytes)
        except Exception:
            pass
        try:
            return parse_csv_bytes(content_bytes)
        except Exception:
            pass
        try:
            return parse_xlsx_bytes(content_bytes)
        except Exception:
            pass
        raise ValueError(f"Unsupported dataset format '.{ext}'. Supported formats: .xlsx, .xls, .csv, .json")

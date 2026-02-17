"""Utilities for parsing and normalizing uploaded tabular files."""

import io
from pathlib import Path
from typing import List

import pandas as pd
from werkzeug.datastructures import FileStorage


ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


class FileParsingError(ValueError):
    """Raised when user-uploaded files cannot be parsed safely."""


def parse_uploaded_file(file_storage: FileStorage) -> pd.DataFrame:
    """Parse an uploaded CSV/Excel file into a cleaned pandas DataFrame."""
    filename = (file_storage.filename or "").strip()
    if not filename:
        raise FileParsingError("Missing filename. Please upload a CSV or Excel file.")

    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise FileParsingError("Unsupported file type. Use .csv, .xlsx, or .xls.")

    raw_bytes = file_storage.read()
    file_storage.stream.seek(0)
    if not raw_bytes:
        raise FileParsingError("Uploaded file is empty.")

    try:
        buffer = io.BytesIO(raw_bytes)
        if extension == ".csv":
            df = pd.read_csv(buffer)
        else:
            df = pd.read_excel(buffer)
    except Exception as error:
        raise FileParsingError("Could not read the uploaded file. Verify the file format and try again.") from error

    if df.empty:
        raise FileParsingError("Uploaded file has no data rows to analyze.")

    df.columns = _normalize_columns(df.columns)
    return df


def _normalize_columns(columns) -> List[str]:
    """Normalize column names and make duplicates deterministic and unique."""
    cleaned = []
    seen = {}

    for idx, column in enumerate(columns):
        name = str(column).strip() if column is not None else ""
        if not name:
            name = f"column_{idx + 1}"
        count = seen.get(name, 0)
        seen[name] = count + 1
        if count > 0:
            name = f"{name}_{count + 1}"
        cleaned.append(name)

    return cleaned

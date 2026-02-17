"""Temporary storage helpers for uploaded datasets."""

import json
import re
import time
import uuid
from pathlib import Path
from typing import Tuple

import pandas as pd


_DATASET_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
_DATASET_FILE_SUFFIX = ".pkl"
_DATASET_META_SUFFIX = ".json"


class DatasetNotFoundError(FileNotFoundError):
    """Raised when a dataset ID is invalid, missing, expired, or unreadable."""


def save_dataset(df: pd.DataFrame, source_filename: str, storage_dir: str) -> str:
    """Persist an uploaded DataFrame and return its generated dataset identifier."""
    storage_path = Path(storage_dir)
    storage_path.mkdir(parents=True, exist_ok=True)

    dataset_id = uuid.uuid4().hex
    dataset_path = _dataset_path(storage_path, dataset_id)
    meta_path = _meta_path(storage_path, dataset_id)

    df.to_pickle(dataset_path)
    meta_path.write_text(
        json.dumps({"source_filename": source_filename or "uploaded_file"}, ensure_ascii=True),
        encoding="utf-8",
    )
    return dataset_id


def load_dataset(dataset_id: str, storage_dir: str, ttl_seconds: int) -> Tuple[pd.DataFrame, str]:
    """Load a stored dataset by ID and enforce a time-to-live policy."""
    storage_path = Path(storage_dir)
    dataset_path = _resolve_dataset_path(dataset_id, storage_path)
    meta_path = _resolve_meta_path(dataset_id, storage_path)

    if not dataset_path.exists():
        raise DatasetNotFoundError("Uploaded dataset was not found.")

    if _is_expired(dataset_path, ttl_seconds):
        _safe_unlink(dataset_path)
        _safe_unlink(meta_path)
        raise DatasetNotFoundError("Uploaded dataset has expired.")

    try:
        df = pd.read_pickle(dataset_path)
    except Exception as error:
        raise DatasetNotFoundError("Uploaded dataset could not be loaded.") from error

    source_filename = "uploaded_file"
    if meta_path.exists():
        try:
            meta_data = json.loads(meta_path.read_text(encoding="utf-8"))
            source_filename = meta_data.get("source_filename") or source_filename
        except Exception:
            pass

    return df, source_filename


def cleanup_expired_datasets(storage_dir: str, ttl_seconds: int) -> int:
    """Delete expired dataset artifacts and return the deleted count."""
    storage_path = Path(storage_dir)
    if not storage_path.exists():
        return 0

    deleted_count = 0
    for dataset_path in storage_path.glob(f"*{_DATASET_FILE_SUFFIX}"):
        if _is_expired(dataset_path, ttl_seconds):
            dataset_id = dataset_path.stem
            _safe_unlink(dataset_path)
            _safe_unlink(_meta_path(storage_path, dataset_id))
            deleted_count += 1

    return deleted_count


def _resolve_dataset_path(dataset_id: str, storage_path: Path) -> Path:
    """Validate dataset ID and return its pickle path."""
    if not _DATASET_ID_PATTERN.match(dataset_id):
        raise DatasetNotFoundError("Invalid dataset identifier.")
    return _dataset_path(storage_path, dataset_id)


def _resolve_meta_path(dataset_id: str, storage_path: Path) -> Path:
    """Validate dataset ID and return its metadata path."""
    if not _DATASET_ID_PATTERN.match(dataset_id):
        raise DatasetNotFoundError("Invalid dataset identifier.")
    return _meta_path(storage_path, dataset_id)


def _dataset_path(storage_path: Path, dataset_id: str) -> Path:
    """Build the pickle file path for a dataset ID."""
    return storage_path / f"{dataset_id}{_DATASET_FILE_SUFFIX}"


def _meta_path(storage_path: Path, dataset_id: str) -> Path:
    """Build the metadata JSON path for a dataset ID."""
    return storage_path / f"{dataset_id}{_DATASET_META_SUFFIX}"


def _is_expired(path: Path, ttl_seconds: int) -> bool:
    """Return True when a file has exceeded its configured TTL."""
    return (time.time() - path.stat().st_mtime) > ttl_seconds


def _safe_unlink(path: Path) -> None:
    """Delete a file path without failing when it is already absent."""
    path.unlink(missing_ok=True)

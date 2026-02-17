"""Temporary storage helpers for generated analysis results."""

import re
import time
import uuid
from pathlib import Path

import pandas as pd


RESULT_FILE_SUFFIX = ".csv"
_RESULT_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


class ResultNotFoundError(FileNotFoundError):
    """Raised when a result ID is invalid, missing, expired, or unreadable."""


def save_result(df: pd.DataFrame, storage_dir: str) -> str:
    """Save a result DataFrame as CSV and return its generated identifier."""
    storage_path = Path(storage_dir)
    storage_path.mkdir(parents=True, exist_ok=True)

    result_id = uuid.uuid4().hex
    result_path = storage_path / f"{result_id}{RESULT_FILE_SUFFIX}"
    df.to_csv(result_path, index=False)
    return result_id


def load_result_csv(result_id: str, storage_dir: str, ttl_seconds: int) -> bytes:
    """Load a saved CSV result payload while enforcing TTL expiration."""
    result_path = _resolve_result_path(result_id, storage_dir)
    if not result_path.exists():
        raise ResultNotFoundError(f"Result {result_id} does not exist.")

    if _is_expired(result_path, ttl_seconds):
        result_path.unlink(missing_ok=True)
        raise ResultNotFoundError(f"Result {result_id} has expired.")

    return result_path.read_bytes()


def cleanup_expired(storage_dir: str, ttl_seconds: int) -> int:
    """Delete expired CSV result artifacts and return the deleted count."""
    storage_path = Path(storage_dir)
    if not storage_path.exists():
        return 0

    deleted_count = 0
    for file_path in storage_path.glob(f"*{RESULT_FILE_SUFFIX}"):
        if _is_expired(file_path, ttl_seconds):
            file_path.unlink(missing_ok=True)
            deleted_count += 1

    return deleted_count


def _resolve_result_path(result_id: str, storage_dir: str) -> Path:
    """Validate result ID format and return the corresponding CSV path."""
    if not _RESULT_ID_PATTERN.match(result_id):
        raise ResultNotFoundError("Invalid result identifier.")
    storage_path = Path(storage_dir)
    return storage_path / f"{result_id}{RESULT_FILE_SUFFIX}"


def _is_expired(path: Path, ttl_seconds: int) -> bool:
    """Return True when a result file has exceeded its configured TTL."""
    return (time.time() - path.stat().st_mtime) > ttl_seconds

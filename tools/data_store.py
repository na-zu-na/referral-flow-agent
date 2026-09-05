"""Read-only access to the bundled Problem B fixture data."""

from __future__ import annotations

import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "data" / "fixtures"

_TABLES = {
    "referrals",
    "specialties",
    "urgency_bands",
    "clinic_slots",
    "patients",
    "contacts",
}
_OBJECTS = {"as_of"}


class DataStoreError(RuntimeError):
    """A stable error code for data failures that tools can translate."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def load_table(name: str, root: str | Path | None = None) -> list[dict[str, Any]]:
    """Return a defensive copy of one allowed list-shaped fixture."""
    if name not in _TABLES:
        raise DataStoreError("UNKNOWN_DATASET", f"Unknown table {name!r}.")
    value = _read_json(name, _root_key(root))
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise DataStoreError(
            "DATA_INVALID_SHAPE", f"Fixture {name!r} must be a list of objects."
        )
    return deepcopy(value)


def load_object(name: str, root: str | Path | None = None) -> dict[str, Any]:
    """Return a defensive copy of one allowed object-shaped fixture."""
    if name not in _OBJECTS:
        raise DataStoreError("UNKNOWN_DATASET", f"Unknown object {name!r}.")
    value = _read_json(name, _root_key(root))
    if not isinstance(value, dict):
        raise DataStoreError(
            "DATA_INVALID_SHAPE", f"Fixture {name!r} must be an object."
        )
    return deepcopy(value)


def clear_cache() -> None:
    """Forget parsed fixtures; useful after regeneration and between tests."""
    _read_json.cache_clear()


def _root_key(root: str | Path | None) -> str:
    return str(Path(root).resolve()) if root is not None else str(FIXTURE_DIR)


@lru_cache(maxsize=None)
def _read_json(name: str, root: str) -> Any:
    path = Path(root) / f"{name}.json"
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as exc:
        raise DataStoreError(
            "DATA_FILE_NOT_FOUND", f"Fixture file {path.name!r} was not found."
        ) from exc
    except OSError as exc:
        raise DataStoreError(
            "DATA_READ_ERROR", f"Fixture file {path.name!r} could not be read."
        ) from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise DataStoreError(
            "DATA_INVALID_JSON", f"Fixture file {path.name!r} is not valid JSON."
        ) from exc

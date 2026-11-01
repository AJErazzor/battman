"""Recorded expected results ("snapshots") for tests that compare Battman with a fixed reference.

Many tests prove Battman's engine and cards behave like the originals they were ported from by
running both side by side. Each of those tests also records what Battman produced, here, in
tests/snapshots/<file>.json. The side-by-side check runs first in the same test, so a snapshot
can only be recorded while Battman still matches the original. Once recorded, the snapshot is
the reference: the side-by-side halves can be retired and the snapshot keeps the proof.

    from .snapshots import assert_snapshot
    assert_snapshot(__file__, "world-17", value)

`value` must be JSON-able (dicts, lists, strings, numbers, booleans, None). Keep it free of
times, random ids and absolute paths, or the snapshot won't repeat.

To record or re-record: run the tests with BATTMAN_UPDATE_SNAPSHOTS=1. Only do that when a
change in behaviour is intended, and say so in the commit message: a re-recorded snapshot is a
change to what Battman is promised to do.
"""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
from typing import Any

try:  # recording may run in several pytest-xdist processes at once
    import fcntl
except ImportError:  # pragma: no cover - Windows: record without -n
    fcntl = None

SNAP_DIR = Path(__file__).parent / "snapshots"
UPDATE = os.environ.get("BATTMAN_UPDATE_SNAPSHOTS") == "1"


@contextlib.contextmanager
def _locked(path: Path):
    SNAP_DIR.mkdir(exist_ok=True)
    with open(path.with_suffix(".lock"), "w", encoding="utf-8") as lock:
        if fcntl:
            fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl:
                fcntl.flock(lock, fcntl.LOCK_UN)


def _file(test_file: str) -> Path:
    return SNAP_DIR / f"{Path(test_file).stem}.json"


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _normalise(value: Any) -> Any:
    """Round-trip through JSON so tuples become lists and keys become strings, as on disk."""
    return json.loads(json.dumps(value, sort_keys=True, ensure_ascii=False))


def assert_snapshot(test_file: str, key: str, value: Any) -> None:
    """Fail unless `value` equals the recorded snapshot `key` for this test file.

    With BATTMAN_UPDATE_SNAPSHOTS=1, record `value` instead (creating or replacing `key`).
    """
    path = _file(test_file)
    value = _normalise(value)
    if UPDATE:
        with _locked(path):
            data = _load(path)
            data[key] = value
            path.write_text(json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        return
    data = _load(path)
    assert key in data, (
        f"No snapshot '{key}' in {path.relative_to(Path(__file__).parent.parent)}. "
        "Record it by running this test with BATTMAN_UPDATE_SNAPSHOTS=1."
    )
    assert value == data[key], (
        f"Battman's result for '{key}' differs from its recorded snapshot in {path.name}: "
        f"{_first_difference(data[key], value)}"
    )


def _first_difference(want: Any, got: Any, where: str = "") -> str:
    """Where the first difference is, and the two values there, kept short for the failure message."""
    if isinstance(want, dict) and isinstance(got, dict):
        for k in sorted(set(want) | set(got), key=str):
            if k not in got:
                return f"{where}/{k} missing (snapshot has {_short(want[k])})"
            if k not in want:
                return f"{where}/{k} is new ({_short(got[k])})"
            if want[k] != got[k]:
                return _first_difference(want[k], got[k], f"{where}/{k}")
    if isinstance(want, list) and isinstance(got, list):
        for i, (a, b) in enumerate(zip(want, got)):
            if a != b:
                return _first_difference(a, b, f"{where}[{i}]")
        if len(want) != len(got):
            return f"{where or 'value'} has {len(got)} items, snapshot has {len(want)}"
    return f"{where or 'value'}: snapshot {_short(want)}, now {_short(got)}"


def _short(v: Any) -> str:
    text = json.dumps(v, ensure_ascii=False)
    return text if len(text) <= 120 else text[:117] + "..."

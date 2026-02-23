"""CSV allow-list loading, polling, and atomic reload."""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

REQUIRED_COLUMNS = {"id", "api_key", "owner", "added"}


@dataclass
class AllowListEntry:
    id: str
    api_key: str
    owner: str
    added: str


class AllowList:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._entries: dict[str, AllowListEntry] = {}
        self._last_mtime: float = 0.0

    def load(self) -> None:
        """Load the CSV file. Raises FileNotFoundError or ValueError on problems."""
        entries = self._parse_csv(self._path)
        self._entries = entries
        self._last_mtime = self._path.stat().st_mtime

    def get(self, api_key: str) -> AllowListEntry | None:
        """O(1) lookup by api_key."""
        return self._entries.get(api_key)

    def reload_if_changed(self) -> None:
        """Check file mtime and reload if changed. Atomic swap of in-memory state."""
        try:
            current_mtime = self._path.stat().st_mtime
        except OSError:
            log.warning("Allow-list file not accessible: %s", self._path)
            return
        if current_mtime != self._last_mtime:
            log.info("Allow-list file changed, reloading: %s", self._path)
            self.load()

    @staticmethod
    def _parse_csv(path: Path) -> dict[str, AllowListEntry]:
        """Parse CSV file into a dict keyed by api_key."""
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                raise ValueError(f"Empty or invalid CSV: {path}")
            missing = REQUIRED_COLUMNS - set(reader.fieldnames)
            if missing:
                raise ValueError(f"CSV missing required columns: {sorted(missing)}")
            entries: dict[str, AllowListEntry] = {}
            for row in reader:
                entry = AllowListEntry(
                    id=row["id"],
                    api_key=row["api_key"],
                    owner=row["owner"],
                    added=row["added"],
                )
                entries[entry.api_key] = entry
            return entries

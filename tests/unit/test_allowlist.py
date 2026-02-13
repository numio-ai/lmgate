"""Tests for lmgate.allowlist — CSV loading, polling, atomic reload."""

import csv
import time
from pathlib import Path

import pytest

from lmgate.allowlist import AllowList, AllowListEntry


@pytest.fixture
def csv_file(tmp_path: Path) -> Path:
    """Create a valid allowlist CSV file."""
    path = tmp_path / "allowlist.csv"
    path.write_text(
        "id,api_key,owner,added\n"
        "1,sk-abc123xyz,team-alpha,2025-01-15\n"
        "2,AKIAIOSFODNN7EXAMPLE,team-beta,2025-02-01\n"
    )
    return path


class TestAllowListLoad:
    def test_load_valid_csv(self, csv_file: Path) -> None:
        al = AllowList(csv_file)
        al.load()
        entry = al.get("sk-abc123xyz")
        assert entry is not None
        assert entry.id == "1"
        assert entry.owner == "team-alpha"
        assert entry.added == "2025-01-15"

    def test_load_multiple_entries(self, csv_file: Path) -> None:
        al = AllowList(csv_file)
        al.load()
        assert al.get("sk-abc123xyz") is not None
        assert al.get("AKIAIOSFODNN7EXAMPLE") is not None

    def test_lookup_missing_key(self, csv_file: Path) -> None:
        al = AllowList(csv_file)
        al.load()
        assert al.get("nonexistent-key") is None

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        al = AllowList(tmp_path / "nonexistent.csv")
        with pytest.raises(FileNotFoundError):
            al.load()

    def test_malformed_csv_missing_columns(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.csv"
        path.write_text("id,api_key\n1,sk-abc\n")
        al = AllowList(path)
        with pytest.raises(ValueError, match="missing.*columns"):
            al.load()

    def test_empty_csv_headers_only(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.csv"
        path.write_text("id,api_key,owner,added\n")
        al = AllowList(path)
        al.load()
        assert al.get("anything") is None


class TestAllowListReload:
    def test_reload_on_mtime_change(self, csv_file: Path) -> None:
        al = AllowList(csv_file)
        al.load()
        assert al.get("sk-abc123xyz") is not None
        assert al.get("sk-newkey999") is None

        # Overwrite file with different content
        time.sleep(0.05)  # ensure mtime differs
        csv_file.write_text(
            "id,api_key,owner,added\n"
            "3,sk-newkey999,team-gamma,2025-03-01\n"
        )

        al.reload_if_changed()
        assert al.get("sk-newkey999") is not None
        assert al.get("sk-abc123xyz") is None  # old key gone

    def test_no_reload_when_unchanged(self, csv_file: Path) -> None:
        al = AllowList(csv_file)
        al.load()
        original_entry = al.get("sk-abc123xyz")

        al.reload_if_changed()
        assert al.get("sk-abc123xyz") is original_entry  # same object, no reload


class TestAllowListEntry:
    def test_entry_fields(self) -> None:
        entry = AllowListEntry(id="1", api_key="sk-abc", owner="team-a", added="2025-01-01")
        assert entry.id == "1"
        assert entry.api_key == "sk-abc"
        assert entry.owner == "team-a"
        assert entry.added == "2025-01-01"

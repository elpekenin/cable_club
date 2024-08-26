"""Poll for changes in the files within a directory."""

from __future__ import annotations

import logging
from pathlib import Path

MAGIC_NUMBER = 3
DirHash = dict[Path, float]  # how a folder's "hash" is represented

_logger = logging.getLogger(__name__)


def rules_changed(directory: Path, old_files_hash: DirHash) -> tuple[bool, DirHash]:
    """Check if directory's contents have changed."""
    if directory.is_dir():
        new_files_hash = {f: f.stat().st_mtime for f in directory.iterdir()}

        changed = old_files_hash.keys() != new_files_hash.keys()
        if not changed:
            for k in old_files_hash.keys() & new_files_hash.keys():
                if old_files_hash[k] != new_files_hash[k]:
                    changed = True
                    break

        if changed:
            _logger.debug("Refreshing Rules due to changes")
            return True, new_files_hash

    return False, old_files_hash


def load_rules(directory: Path, files_hash: DirHash) -> list[list[str]]:
    """Load up rules from a directory."""
    rules = []
    for f in iter(files_hash):
        rule = []
        with (directory / f).open() as rule_file:
            for num, raw in enumerate(rule_file):
                line = raw.strip()
                if num == MAGIC_NUMBER:
                    rule.extend(line.split(","))
                else:
                    rule.append(line)
        rules.append(rule)
    return rules

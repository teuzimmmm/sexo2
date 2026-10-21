"""Move files that older versions named after the base project to their SEXO2 name.

The data folder keeps its place, but the files inside it were renamed. A file
with the old name is renamed when the new one does not exist yet, so nothing is
lost and a second call changes nothing. When the rename fails (the file is open
in an older version that is still running), the old file keeps being used.
"""

from __future__ import annotations

import os
from pathlib import Path


def migrate_file(folder: Path, old_name: str, new_name: str) -> Path:
    """The path to use for a file: the new name, or the old one if it could not be moved."""
    new_path = Path(folder) / new_name
    old_path = Path(folder) / old_name
    if new_path.exists() or not old_path.exists():
        return new_path
    try:
        os.replace(old_path, new_path)
    except OSError:
        return old_path
    return new_path

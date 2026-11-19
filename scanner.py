"""Read-only discovery of video files and dates in their names."""

import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class VideoRecord:
    """A discovered file and its filename date, or None for an invalid date."""

    path: Path
    date: date | None


def scan_videos(
    source: Path, extensions: Iterable[str], recursive: bool
) -> list[VideoRecord]:
    """Return matching files without modifying them; ordering is unspecified.

    Extensions are case-insensitive and may include a leading dot. Dates must
    start the filename in YYYY-MM-DD format and be valid calendar dates. Any
    following filename text, including a time, is ignored. Invalid or missing
    dates produce None. Recursive scans do not follow directory symlinks.
    Filesystem errors propagate to the caller.
    """
    suffixes = {
        (extension if extension.startswith(".") else "." + extension).casefold()
        for extension in extensions
    }
    records: list[VideoRecord] = []
    pending = [source]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                if recursive and entry.is_dir(follow_symlinks=False):
                    pending.append(Path(entry.path))
                elif entry.is_file() and Path(entry.name).suffix.casefold() in suffixes:
                    match = re.match(r"^([0-9]{4}-[0-9]{2}-[0-9]{2})", entry.name)
                    try:
                        file_date = date.fromisoformat(match.group(1)) if match else None
                    except ValueError:
                        file_date = None
                    records.append(VideoRecord(Path(entry.path), file_date))
    return records

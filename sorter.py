"""Coordinate validation, discovery, conflict decisions and file transfers."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from file_operations import transfer_file
from scanner import scan_videos
from validation import validate_paths


@dataclass(frozen=True)
class ProcessedFile:
    source: Path
    destination: Path


@dataclass(frozen=True)
class SkippedFile:
    source: Path
    reason: str


@dataclass(frozen=True)
class FileError:
    source: Path
    destination: Path
    error: Exception
    possibly_partial: bool = False


@dataclass
class SortReport:
    processed: list[ProcessedFile] = field(default_factory=list)
    skipped: list[SkippedFile] = field(default_factory=list)
    errors: list[FileError] = field(default_factory=list)
    cancelled: bool = False


def sort_videos(
    source: str | Path,
    destination: str | Path,
    extensions: Iterable[str],
    recursive: bool,
    mode: str,
    resolve_conflict: Callable[[Path], str],
) -> SortReport:
    """Sort discovered videos; invalid arguments and scan errors propagate.

    Conflict decisions are requested separately for every conflict. File errors
    are recorded and processing continues; a move error during transfer is
    conservatively marked as possibly partial.
    """
    error = validate_paths(str(source), str(destination), recursive)
    if error:
        raise ValueError(error)
    if mode not in ("copy", "move"):
        raise ValueError("mode must be 'copy' or 'move'")
    source, destination = Path(source), Path(destination)
    records = scan_videos(source, extensions, recursive)
    report = SortReport()
    for record in records:
        if record.date is None:
            report.skipped.append(SkippedFile(record.path, "invalid_date"))
            continue
        target = destination / record.date.strftime("%d.%m.%y") / record.path.name
        transferring = False
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                result = None
            else:
                transferring = True
                result = transfer_file(record.path, target, mode=mode)
                transferring = False
            if result is None:
                decision = resolve_conflict(target)
                if decision not in ("skip", "rename", "replace", "cancel"):
                    raise ValueError("invalid conflict decision")
                if decision == "cancel":
                    report.cancelled = True
                    break
                if decision == "skip":
                    report.skipped.append(SkippedFile(record.path, "conflict"))
                    continue
                transferring = True
                result = transfer_file(record.path, target, mode=mode, conflict=decision)
                transferring = False
            report.processed.append(ProcessedFile(record.path, result))
        except OSError as exc:
            report.errors.append(
                FileError(record.path, target, exc, mode == "move" and transferring)
            )
        except ValueError as exc:
            if str(exc) == "invalid conflict decision":
                raise
            report.errors.append(FileError(record.path, target, exc))
    return report

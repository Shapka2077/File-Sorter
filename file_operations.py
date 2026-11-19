"""Safe single-file copy and move operations.

transfer_file(source, destination, *, mode, conflict="skip") -> Path | None

Both paths identify files (not directories); the destination parent must
already exist. mode is "copy" or "move". conflict is "skip", "rename", or
"replace"; only "replace" authorizes overwriting an existing destination.
The returned Path is the actual destination, or None when a conflict is
skipped. Invalid options and a destination identifying the source raise
ValueError; filesystem errors propagate as OSError.

Copying is staged in the destination directory. Skip and rename publish with
an atomic hard-link operation, requiring hard-link support on that filesystem.
Replace atomically replaces the directory entry after staging. A move removes
the source only after publication; if removal fails, both copies remain and
the exception propagates. This is not a transaction against external changes:
concurrent modification or replacement of the source cannot be fully ruled
out between the final identity check and removal. Cancellation and conflict
prompts belong to the caller.
"""

import os
import shutil
import stat
import tempfile
from pathlib import Path


def transfer_file(source, destination, *, mode, conflict="skip"):
    """Copy or move one regular file; see the module documentation for the API."""
    if mode not in ("copy", "move"):
        raise ValueError("mode must be 'copy' or 'move'")
    if conflict not in ("skip", "rename", "replace"):
        raise ValueError("conflict must be 'skip', 'rename', or 'replace'")

    source = Path(source)
    destination = Path(destination)
    if source.resolve() == destination.resolve():
        raise ValueError("source and destination identify the same file")
    try:
        if os.path.samefile(source, destination):
            raise ValueError("source and destination identify the same file")
    except FileNotFoundError:
        pass

    with source.open("rb") as input_file:
        source_stat = os.fstat(input_file.fileno())
        if not stat.S_ISREG(source_stat.st_mode):
            raise ValueError("source must be a regular file")

        fd, temporary_name = tempfile.mkstemp(
            prefix=".file-sorter-", suffix=".tmp", dir=destination.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(fd, "wb") as output_file:
                shutil.copyfileobj(input_file, output_file)
            input_file.close()

            if conflict == "replace":
                os.replace(temporary, destination)
                result = destination
            else:
                result = destination
                suffix = 0
                while True:
                    try:
                        os.link(temporary, result)
                        break
                    except FileExistsError:
                        if conflict == "skip":
                            return None
                        suffix += 1
                        result = destination.with_name(
                            f"{destination.stem} ({suffix}){destination.suffix}"
                        )

            if mode == "move":
                current = source.stat()
                if (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns) != (
                    source_stat.st_dev, source_stat.st_ino,
                    source_stat.st_size, source_stat.st_mtime_ns,
                ):
                    raise OSError("source changed during transfer; source was not removed")
                source.unlink()
            return result
        finally:
            temporary.unlink(missing_ok=True)

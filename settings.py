import json
import os
import re
import tempfile
from pathlib import Path

DEFAULT_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv", ".wmv", ".m4v", ".webm")


def _normalize_extensions(extensions):
    result = []
    for extension in extensions:
        if not isinstance(extension, str):
            raise ValueError("Расширения должны быть строками.")
        extension = extension.strip().lower()
        if not extension.startswith("."):
            extension = "." + extension
        if not re.fullmatch(r"\.[a-z0-9]+", extension):
            raise ValueError(f"Некорректное расширение: {extension}")
        if extension not in result:
            result.append(extension)
    if not result:
        raise ValueError("Укажите хотя бы одно расширение.")
    return tuple(result)


def load_extensions(path: Path) -> tuple[str, ...]:
    try:
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        return DEFAULT_EXTENSIONS
    except (json.JSONDecodeError, UnicodeError) as error:
        raise ValueError("Не удалось прочитать настройки форматов.") from error
    if not isinstance(data, dict) or not isinstance(data.get("extensions"), list):
        raise ValueError("Некорректные настройки форматов.")
    return _normalize_extensions(data["extensions"])


def save_extensions(path: Path, extensions) -> None:
    normalized = _normalize_extensions(extensions)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as file:
            temp_path = Path(file.name)
            json.dump({"extensions": normalized}, file, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

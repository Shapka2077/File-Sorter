from pathlib import Path


def validate_paths(source: str, destination: str, recursive: bool = False) -> str | None:
    if not source.strip() or not destination.strip():
        return "Выберите обе папки."

    source_path = Path(source)
    destination_path = Path(destination)
    try:
        if not source_path.is_dir():
            return "Исходная папка не существует или недоступна."
        if not destination_path.is_dir():
            return "Папка назначения не существует или недоступна."
        if source_path.samefile(destination_path):
            return "Исходная папка и папка назначения должны различаться."
        if recursive and destination_path.resolve().is_relative_to(source_path.resolve()):
            return "При поиске в подпапках папка назначения не может находиться внутри исходной."
    except (OSError, ValueError):
        return "Не удалось проверить выбранные папки."
    return None

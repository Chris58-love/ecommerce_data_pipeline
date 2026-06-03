from pathlib import Path
from typing import List

from src.models import FileRecord


SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv"}


def should_ignore(path: Path) -> bool:
    return (
        any(part in {"__MACOSX", ".DS_Store"} for part in path.parts)
        or path.name.startswith("~$")
        or path.name == ".DS_Store"
    )


def scan_table_files(input_dir: str) -> List[FileRecord]:
    root = Path(input_dir).resolve()
    records = []
    for path in root.rglob("*"):
        if should_ignore(path) or not path.is_file():
            continue
        ext = path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue
        records.append(
            FileRecord(
                path=str(path),
                filename=path.name,
                parent_dir=path.parent.name,
                relative_path=str(path.relative_to(root)),
                extension=ext,
            )
        )
    return records

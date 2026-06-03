import os
import zipfile
from pathlib import Path


IGNORED_NAMES = {"__MACOSX", ".DS_Store"}


def prepare_input_path(input_path: str, temp_dir: str) -> str:
    path = Path(input_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"输入路径不存在: {path}")
    if path.is_dir():
        return str(path)
    if path.suffix.lower() == ".zip":
        extract_dir = Path(temp_dir).resolve() / "unzipped_input"
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "r") as zipf:
            for member in zipf.infolist():
                parts = Path(member.filename).parts
                if any(part in IGNORED_NAMES for part in parts):
                    continue
                zipf.extract(member, extract_dir)
        return str(extract_dir)
    raise ValueError("输入路径必须是文件夹或 ZIP 文件。")

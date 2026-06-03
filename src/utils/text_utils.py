import re
import unicodedata
from typing import Iterable, Optional, Set


def normalize_text(value) -> str:
    if value is None:
        return ""
    text = str(value)
    if text.lower() in {"nan", "none", "null"}:
        return ""
    text = unicodedata.normalize("NFKC", text)
    return text.replace("\u3000", " ").strip()


def normalize_col_name(value) -> str:
    return re.sub(r"[\s_\-—－~～]", "", normalize_text(value)).lower()


def sanitize_filename_part(text: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]', "_", normalize_text(text))
    cleaned = re.sub(r"\s+", "", cleaned)
    return cleaned or "未命名"


def safe_sheet_name(name: str, used_names: Optional[Set[str]] = None) -> str:
    cleaned = re.sub(r"[\[\]:*?/\\]", "_", normalize_text(name)) or "Sheet"
    cleaned = cleaned[:31]
    if used_names is None:
        return cleaned
    candidate = cleaned
    suffix = 1
    while candidate in used_names:
        suffix_text = f"_{suffix}"
        candidate = f"{cleaned[:31 - len(suffix_text)]}{suffix_text}"
        suffix += 1
    used_names.add(candidate)
    return candidate


def extract_keyword_from_folder_name(folder_name: str) -> str:
    text = normalize_text(folder_name)
    for pattern in [
        r"(?:京东|JD|jd|jingdong)\s*数据?\s*[-_—－]?\s*(.+)$",
        r"(?:抖音|douyin|dy)\s*数据?\s*[-_—－]?\s*(.+)$",
    ]:
        match = re.search(pattern, text, flags=re.I)
        if match:
            return normalize_text(match.group(1))
    return ""


def unique_column_name(existing_columns: Iterable, preferred_name: str) -> str:
    existing = {str(col) for col in existing_columns}
    if preferred_name not in existing:
        return preferred_name
    index = 1
    while f"{preferred_name}_{index}" in existing:
        index += 1
    return f"{preferred_name}_{index}"

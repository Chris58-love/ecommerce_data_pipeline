THRESHOLDS = {
    "platform_detection": 0.75,
    "keyword_extraction": 0.75,
    "column_mapping": 0.80,
    "date_inference": 0.85,
    "category_review": 0.70,
    "numeric_auto_apply": 0.90,
    "merge_consistency_review": 0.75,
}


def threshold(name: str, default: float = 0.75) -> float:
    return THRESHOLDS.get(name, default)

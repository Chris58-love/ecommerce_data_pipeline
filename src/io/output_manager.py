from datetime import datetime
from pathlib import Path


def create_output_dir(base_output_dir: str, timestamp_output_dir: bool = True) -> dict:
    base = Path(base_output_dir).expanduser().resolve()
    if timestamp_output_dir:
        run_dir = base / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    else:
        run_dir = base
    for sub in ["workbooks", "reports", "logs", "temp"]:
        (run_dir / sub).mkdir(parents=True, exist_ok=True)
    return {
        "root": str(run_dir),
        "workbooks": str(run_dir / "workbooks"),
        "reports": str(run_dir / "reports"),
        "logs": str(run_dir / "logs"),
        "temp": str(run_dir / "temp"),
    }

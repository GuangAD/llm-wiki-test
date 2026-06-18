from pathlib import Path


def dated_dir(root: Path, base: str, date_yyyymmdd: str) -> Path:
    return root / base / date_yyyymmdd

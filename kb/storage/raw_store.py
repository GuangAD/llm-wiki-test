from pathlib import Path

from kb.core.atomic import atomic_write_text


def write_raw(
    root: Path,
    date_yyyymmdd: str,
    content_id: str,
    text: str,
    meta_yaml: str,
) -> tuple[Path, Path]:
    raw_dir = root / "raw" / date_yyyymmdd
    raw_path = raw_dir / f"{content_id}.md"
    meta_path = raw_dir / f"{content_id}.meta.yaml"
    atomic_write_text(raw_path, text)
    atomic_write_text(meta_path, meta_yaml)
    return raw_path, meta_path


def find_existing_content_by_hash(root: Path, content_hash: str) -> tuple[str, Path] | None:
    import yaml

    for meta_path in (root / "raw").glob("**/*.meta.yaml"):
        data = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        if data.get("content_hash") == content_hash:
            return data["id"], meta_path
    return None

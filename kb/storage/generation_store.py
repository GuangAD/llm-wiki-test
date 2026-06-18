from pathlib import Path

import frontmatter
import yaml

from kb.core.atomic import atomic_write_text
from kb.core.models import GenerationResult


def request_path(root: Path, job_id: str, generation_type: str) -> Path:
    return root / "state" / "generation_requests" / f"{job_id}-{generation_type}.md"


def result_path(root: Path, job_id: str, generation_type: str) -> Path:
    return root / "state" / "generation_results" / f"{job_id}-{generation_type}.yaml"


def write_generation_request(
    root: Path,
    job_id: str,
    generation_type: str,
    metadata: dict,
    body: str,
) -> Path:
    path = request_path(root, job_id, generation_type)
    post = frontmatter.Post(body, **metadata)
    atomic_write_text(path, frontmatter.dumps(post))
    return path


def read_generation_result(root: Path, job_id: str, generation_type: str) -> GenerationResult:
    path = result_path(root, job_id, generation_type)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return GenerationResult.model_validate(data)

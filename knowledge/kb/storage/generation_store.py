from pathlib import Path

import frontmatter
import yaml

from kb.core.atomic import atomic_write_text
from kb.core.models import GenerationResult


def _suffix(generation_type: str, scope_key: str | None = None) -> str:
    return f"{generation_type}-{scope_key}" if scope_key else generation_type


def request_path(
    root: Path,
    job_id: str,
    generation_type: str,
    scope_key: str | None = None,
) -> Path:
    return root / "state" / "generation_requests" / f"{job_id}-{_suffix(generation_type, scope_key)}.md"


def result_path(
    root: Path,
    job_id: str,
    generation_type: str,
    scope_key: str | None = None,
) -> Path:
    return root / "state" / "generation_results" / f"{job_id}-{_suffix(generation_type, scope_key)}.yaml"


def write_generation_request(
    root: Path,
    job_id: str,
    generation_type: str,
    metadata: dict,
    body: str,
    scope_key: str | None = None,
) -> Path:
    path = request_path(root, job_id, generation_type, scope_key)
    post = frontmatter.Post(body, **metadata)
    atomic_write_text(path, frontmatter.dumps(post))
    return path


def _existing_path(primary: Path, legacy: Path | None = None) -> Path:
    if primary.exists() or legacy is None:
        return primary
    return legacy


def read_generation_result(
    root: Path,
    job_id: str,
    generation_type: str,
    scope_key: str | None = None,
) -> GenerationResult:
    legacy_result = result_path(root, job_id, generation_type) if scope_key else None
    path = _existing_path(result_path(root, job_id, generation_type, scope_key), legacy_result)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    result = GenerationResult.model_validate(data)

    legacy_request = request_path(root, job_id, generation_type) if scope_key else None
    request_file = _existing_path(
        request_path(root, job_id, generation_type, scope_key),
        legacy_request,
    )
    request = frontmatter.loads(request_file.read_text(encoding="utf-8")).metadata
    expected = {
        "request_id": request.get("request_id"),
        "job_id": job_id,
        "generation_type": generation_type,
    }
    actual = {
        "request_id": result.request_id,
        "job_id": result.job_id,
        "generation_type": result.generation_type,
    }
    if actual != expected:
        raise ValueError("generation result does not match request identity")
    if request.get("content_id") and result.content_id != request["content_id"]:
        raise ValueError("generation result content_id does not match request")
    if scope_key and request.get("topic_key") != scope_key:
        raise ValueError("generation request scope does not match topic_key")

    allowed_sources = {str(item) for item in request.get("source_paths", [])}
    result_sources = {source.path for source in result.sources}
    if not result_sources.issubset(allowed_sources):
        raise ValueError("generation result contains sources outside request")
    return result

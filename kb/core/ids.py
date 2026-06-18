from hashlib import sha256


def source_key_hash(source_key: str) -> str:
    return sha256(source_key.encode("utf-8")).hexdigest()[:8]


def build_content_id(date_yyyymmdd: str, source_key: str) -> str:
    return f"cnt_{date_yyyymmdd}_{source_key_hash(source_key)}"


def build_note_id(date_yyyymmdd: str, source_key: str) -> str:
    return f"note_{date_yyyymmdd}_{source_key_hash(source_key)}"


def build_note_id_from_content_id(content_id: str) -> str:
    _, date_yyyymmdd, hash_part = content_id.split("_", maxsplit=2)
    return f"note_{date_yyyymmdd}_{hash_part}"


def build_job_id(timestamp_yyyymmddhhmmss: str, source_key: str) -> str:
    return f"job_{timestamp_yyyymmddhhmmss}_{source_key_hash(source_key)}"


def build_request_id(timestamp_yyyymmddhhmmss: str, source_key: str, generation_type: str) -> str:
    return f"gen_{timestamp_yyyymmddhhmmss}_{source_key_hash(source_key)}_{generation_type}"

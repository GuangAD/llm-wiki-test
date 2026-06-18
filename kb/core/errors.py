def error_response(
    command: str,
    status: str,
    error_code: str,
    error_message: str,
    retryable: bool,
    next_action: str,
    job_id: str | None = None,
) -> dict:
    data = {
        "ok": False,
        "command": command,
        "status": status,
        "error_code": error_code,
        "error_message": error_message,
        "retryable": retryable,
        "next_action": next_action,
    }
    if job_id:
        data["job_id"] = job_id
    return data

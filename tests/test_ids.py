from kb.core.ids import (
    build_content_id,
    build_job_id,
    build_note_id,
    build_note_id_from_content_id,
    build_request_id,
)


def test_content_and_note_ids_use_same_date_hash():
    content_id = build_content_id("20260618", "https://example.com/article")
    note_id = build_note_id("20260618", "https://example.com/article")

    assert content_id.startswith("cnt_20260618_")
    assert note_id.startswith("note_20260618_")
    assert content_id.split("_")[-1] == note_id.split("_")[-1]


def test_note_id_can_be_derived_from_content_id():
    assert build_note_id_from_content_id("cnt_20260618_a8f31c92") == "note_20260618_a8f31c92"


def test_job_and_request_ids_include_timestamp_and_type():
    source = "https://example.com/article"

    job_id = build_job_id("20260618143022", source)
    request_id = build_request_id("20260618143022", source, "note")

    assert job_id.startswith("job_20260618143022_")
    assert request_id.startswith("gen_20260618143022_")
    assert request_id.endswith("_note")

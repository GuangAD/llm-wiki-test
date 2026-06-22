import re


def slugify_topic_key(value: str) -> str:
    words = re.findall(r"[\w]+", value.lower(), flags=re.UNICODE)
    return "-".join(words)


def extract_topic_keys(values: list[str]) -> list[str]:
    keys = [slugify_topic_key(value) for value in values]
    return sorted({key for key in keys if key})

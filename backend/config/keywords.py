import yaml
from pathlib import Path

from settings import config


def read_keywords() -> list[str]:
    """Read keywords.yaml and return a flat list of all keywords."""
    path = Path(config.KEYWORDS_CONFIG_PATH)
    if not path.exists():
        raise FileNotFoundError(f"Keywords config not found: {path.resolve()}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    keywords: list[str] = []
    target = data.get("target_keywords", {})
    for lang in ("en", "zh"):
        for kw in target.get(lang, []):
            keywords.append(str(kw))

    return keywords

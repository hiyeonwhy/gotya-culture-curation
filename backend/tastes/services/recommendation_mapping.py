import json
from functools import lru_cache
from pathlib import Path


CONFIG_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "taste_test_config.json"
SOURCE_CONFIG_PATH = Path(__file__).resolve().parents[3] / "api_extract" / "taste_test_config.json"


def _load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _merge_configs(source_config, fixture_config):
    merged = dict(source_config)
    fixture_mapping = fixture_config.get("recommendation_db_mapping", {})
    if fixture_mapping:
        merged["recommendation_db_mapping"] = fixture_mapping
    elif "recommendation_db_mapping" in source_config:
        merged["recommendation_db_mapping"] = source_config["recommendation_db_mapping"]
    else:
        merged["recommendation_db_mapping"] = {}
    return merged


@lru_cache(maxsize=1)
def load_taste_config():
    fixture_config = _load_json(CONFIG_PATH)
    source_config = _load_json(SOURCE_CONFIG_PATH) if SOURCE_CONFIG_PATH.exists() else fixture_config
    config = _merge_configs(source_config, fixture_config)

    result_types = config.get("result_types", [])
    result_codes = {row.get("code") for row in result_types}
    db_mapping = config.get("recommendation_db_mapping", {})
    if not result_codes or result_codes != set(db_mapping):
        raise ValueError("취향 유형과 recommendation_db_mapping 구성이 일치하지 않습니다.")
    return config


TASTE_CONFIG = load_taste_config()
RESULT_TYPE_BY_CODE = {
    row["code"]: row for row in TASTE_CONFIG["result_types"]
}
TASTE_LABELS = {
    code: row["name"] for code, row in RESULT_TYPE_BY_CODE.items()
}
TASTE_CONTENT_MAPPING = TASTE_CONFIG["recommendation_db_mapping"]


def get_ai_taste_guide(taste_type):
    result = RESULT_TYPE_BY_CODE[taste_type]
    return {
        "code": result["code"],
        "name": result["name"],
        "base_type": result["base_type"],
        "subtitle": result["subtitle"],
        "summary": result["summary"],
        "description": result["description"],
        "keywords": result["keywords"],
        "recommendation_guide": result["recommendation"],
        "result_keywords": TASTE_CONFIG["result_keyword_map"].get(taste_type, []),
    }

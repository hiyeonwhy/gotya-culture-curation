import hashlib
import json

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .candidate_selector import select_candidates
from .gms_client import GMSClient, GMSResponseError, GMSUnavailableError
from .profile_builder import build_user_profile


CONTENT_TYPES = ("movie", "book", "culture")
TASTE_TYPES = (
    "TREND",
    "MONGLE",
    "WORLD",
    "KNOWLEDGE",
    "FESTIVAL",
    "TOGETHER",
)


def _score_percentages(score_data):
    if isinstance(score_data, dict) and isinstance(score_data.get("type_scores"), dict):
        score_data = score_data["type_scores"]
    scores = {}
    for taste_type in TASTE_TYPES:
        try:
            scores[taste_type] = max(float(score_data.get(taste_type, 0)), 0)
        except (AttributeError, TypeError, ValueError):
            scores[taste_type] = 0

    total = sum(scores.values())
    if not total:
        return {taste_type: 0 for taste_type in TASTE_TYPES}

    raw = {taste_type: score / total * 100 for taste_type, score in scores.items()}
    rounded = {taste_type: round(value, 1) for taste_type, value in raw.items()}
    difference = round(100 - sum(rounded.values()), 1)
    if difference:
        largest = max(raw, key=raw.get)
        rounded[largest] = round(rounded[largest] + difference, 1)
    return rounded


def _default_reason(profile, candidate):
    metadata = candidate["metadata"]
    labels = (
        metadata.get("genres")
        or metadata.get("categories")
        or [metadata.get("sub_category")]
    )
    labels = [label for label in labels if label]
    label_text = ", ".join(labels[:2])
    if label_text:
        return f"{profile['taste_label']} 취향과 잘 맞는 {label_text} 콘텐츠입니다."
    return f"{profile['taste_label']} 취향과 인기도를 함께 고려한 추천입니다."


def _validate_and_fill(ai_result, candidates, profile, per_type):
    raw_recommendations = ai_result.get("recommendations", {})
    validated = {}
    used_ids = set()

    for content_type in CONTENT_TYPES:
        candidate_by_id = {
            row["content_item_id"]: row for row in candidates[content_type]
        }
        selected = []
        raw_rows = raw_recommendations.get(content_type, [])
        if not isinstance(raw_rows, list):
            raw_rows = []

        for raw in raw_rows:
            raw_id = raw.get("content_item_id") if isinstance(raw, dict) else raw
            try:
                content_id = int(raw_id)
            except (TypeError, ValueError):
                continue
            if content_id in used_ids or content_id not in candidate_by_id:
                continue
            candidate = candidate_by_id[content_id]
            reason = ""
            if isinstance(raw, dict):
                reason = str(raw.get("reason") or "").strip()[:300]
            selected.append((candidate, reason or _default_reason(profile, candidate)))
            used_ids.add(content_id)
            if len(selected) >= per_type:
                break

        for candidate in candidates[content_type]:
            content_id = candidate["content_item_id"]
            if len(selected) >= per_type:
                break
            if content_id in used_ids:
                continue
            selected.append((candidate, _default_reason(profile, candidate)))
            used_ids.add(content_id)
        validated[content_type] = selected
    return validated


def _serialize_recommendation(candidate, reason):
    content = candidate["content_item"]
    return {
        "content_item_id": content.id,
        "content_type": content.content_type,
        "title": content.title,
        "summary": content.summary,
        "thumbnail_url": _thumbnail_url(content),
        "source_url": content.source_url,
        "popularity_score": content.popularity_score,
        "reason": reason,
        "metadata": candidate["metadata"],
    }


def _thumbnail_url(content):
    url = content.thumbnail_url
    if content.content_type == "book" and url and "image.aladin.co.kr" in url:
        return url.replace("/coversum/", "/cover500/")
    return url


def _serialize_result(profile, selected, source, warning=None, cached=False):
    return {
        "source": source,
        "warning": warning,
        "cached": cached,
        "generated_at": timezone.now(),
        "profile": {
            "is_authenticated": profile["is_authenticated"],
            "selection_source": profile["selection_source"],
            "taste_type": profile["taste_type"],
            "taste_label": profile["taste_label"],
            "result_taste_type": profile["result_taste_type"],
            "result_taste_label": profile["result_taste_label"],
            "score_percentages": _score_percentages(profile["score_data"]),
            "keywords": profile["keywords"],
        },
        "recommendations": {
            content_type: [
                _serialize_recommendation(candidate, reason)
                for candidate, reason in selected[content_type]
            ]
            for content_type in CONTENT_TYPES
        },
    }


def _gms_cache_key(profile, candidates, per_type):
    cache_data = {
        "taste_type": profile["taste_type"],
        "score_data": profile["score_data"],
        "keywords": profile["keywords"],
        "liked_titles": profile["liked_titles"],
        "bookmarked_titles": profile["bookmarked_titles"],
        "per_type": per_type,
        "candidate_ids": {
            content_type: [row["content_item_id"] for row in rows]
            for content_type, rows in candidates.items()
        },
    }
    serialized = json.dumps(cache_data, ensure_ascii=True, sort_keys=True, default=str)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return f"taste-recommendations:{digest}"


def generate_database_recommendations(
    user,
    taste_type=None,
    per_type=10,
    exclude_content_ids=None,
):
    profile = build_user_profile(user, requested_taste_type=taste_type)
    candidates = select_candidates(
        profile,
        limit_per_type=per_type,
        exclude_content_ids=exclude_content_ids,
    )
    selected = _validate_and_fill(
        {"recommendations": {}},
        candidates,
        profile,
        per_type,
    )
    return _serialize_result(profile, selected, source="database_preview")


def generate_recommendations(
    user,
    taste_type=None,
    per_type=3,
    exclude_content_ids=None,
):
    profile = build_user_profile(user, requested_taste_type=taste_type)
    candidate_limit = max(
        per_type,
        min(settings.GMS_CANDIDATES_PER_TYPE, max(per_type, 6)),
    )
    candidates = select_candidates(
        profile,
        limit_per_type=candidate_limit,
        exclude_content_ids=exclude_content_ids,
    )

    source = "gms"
    warning = None
    cached = False
    client = GMSClient()
    ai_per_type = min(per_type, 3)
    cache_key = _gms_cache_key(profile, candidates, ai_per_type)
    ai_result = cache.get(cache_key)
    if ai_result is not None:
        cached = True
    else:
        try:
            ai_result = client.generate(profile, candidates, ai_per_type)
            cache.set(cache_key, ai_result, timeout=600)
        except (GMSUnavailableError, GMSResponseError) as error:
            source = "database_fallback"
            warning = str(error)
            ai_result = {"recommendations": {}}

    selected = _validate_and_fill(ai_result, candidates, profile, per_type)
    return _serialize_result(
        profile,
        selected,
        source=source,
        warning=warning,
        cached=cached,
    )

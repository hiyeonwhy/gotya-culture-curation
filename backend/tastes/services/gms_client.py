import json

import httpx
from django.conf import settings


class GMSUnavailableError(RuntimeError):
    pass


class GMSResponseError(RuntimeError):
    pass


class GMSClient:
    """OpenAI Chat Completions 호환 GMS 엔드포인트 클라이언트."""

    @property
    def enabled(self):
        return bool(settings.GMS_API_URL and settings.GMS_API_KEY)

    def generate(self, profile, candidates, per_type):
        if not self.enabled:
            raise GMSUnavailableError("GMS 설정이 없어 DB fallback을 사용합니다.")

        taste_guide = profile["taste_guide"]
        safe_profile = {
            "taste_type": profile["taste_type"],
            "taste_label": profile["taste_label"],
            "taste_guide": {
                "summary": taste_guide["summary"],
                "recommendation_guide": taste_guide["recommendation_guide"],
                "result_keywords": taste_guide["result_keywords"],
            },
            "score_data": profile["score_data"],
            "keywords": profile["keywords"],
            "liked_titles": profile["liked_titles"],
            "bookmarked_titles": profile["bookmarked_titles"],
        }
        candidate_prompt_limit = max(per_type + 3, 6)
        safe_candidates = {
            content_type: [
                {
                    key: value
                    for key, value in candidate.items()
                    if key not in {"content_item", "summary"}
                }
                for candidate in rows[:candidate_prompt_limit]
            ]
            for content_type, rows in candidates.items()
        }
        prompt_data = {
            "user_profile": safe_profile,
            "per_type": per_type,
            "candidates": safe_candidates,
        }
        system_prompt = (
            "당신은 문화 콘텐츠 순위 엔진입니다. 사용자 취향에 맞춰 제공된 "
            "candidates 안의 content_item_id만 고르세요. 새 ID를 만들거나 중복 "
            "선택하지 마세요. movie, book, culture별로 정확히 per_type개를 "
            "선호도 순으로 선택하세요. 설명이나 추천 이유를 쓰지 말고 다음처럼 "
            "ID 배열만 담은 JSON을 반환하세요: {\"recommendations\": "
            "{\"movie\": [1, 2], \"book\": [3, 4], \"culture\": [5, 6]}}"
        )
        payload = {
            "model": settings.GMS_MODEL,
            "messages": [
                {"role": "developer", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(prompt_data, ensure_ascii=False),
                },
            ],
        }
        headers = {
            "Authorization": f"Bearer {settings.GMS_API_KEY}",
            "Content-Type": "application/json",
        }

        try:
            response = httpx.post(
                settings.GMS_API_URL,
                headers=headers,
                json=payload,
                timeout=settings.GMS_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as error:
            try:
                detail = error.response.json()
            except ValueError:
                detail = error.response.text[:500]
            raise GMSUnavailableError(
                f"GMS 호출 실패 ({error.response.status_code}): {detail}"
            ) from error
        except (httpx.RequestError, ValueError) as error:
            raise GMSUnavailableError(f"GMS 호출 실패: {error}") from error

        return self._extract_result(data)

    def _extract_result(self, data):
        if isinstance(data.get("recommendations"), dict):
            return data

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise GMSResponseError("GMS 응답에서 추천 JSON을 찾을 수 없습니다.") from error

        if isinstance(content, dict):
            return content
        if not isinstance(content, str):
            raise GMSResponseError("GMS 응답 content가 문자열 또는 객체가 아닙니다.")

        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```")
            cleaned = cleaned.removesuffix("```").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as error:
            raise GMSResponseError("GMS가 유효한 JSON을 반환하지 않았습니다.") from error

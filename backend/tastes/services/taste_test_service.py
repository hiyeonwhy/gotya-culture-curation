from django.db import transaction
from rest_framework.exceptions import ValidationError

from tastes.models import (
    Keyword,
    TasteQuestion,
    TasteResult,
    TasteTestConfig,
    TasteTypeDefinition,
    UserKeyword,
)
from tastes.services.recommendation_mapping import load_taste_config


TASTE_TYPE_ORDER = (
    "TREND",
    "MONGLE",
    "WORLD",
    "KNOWLEDGE",
    "FESTIVAL",
    "TOGETHER",
)


def _question_key(row):
    return row.get("question_id", row.get("id"))


def _extract_type_scores(score_data):
    if not isinstance(score_data, dict):
        return {}
    type_scores = score_data.get("type_scores")
    if isinstance(type_scores, dict):
        return type_scores
    return score_data


def _extract_axis_scores(score_data):
    if not isinstance(score_data, dict):
        return {}
    axis_scores = score_data.get("axis_scores")
    return axis_scores if isinstance(axis_scores, dict) else {}


def _percentages(scores):
    scores = _extract_type_scores(scores)
    normalized_scores = {
        code: max(float(scores.get(code, 0)), 0)
        for code in TASTE_TYPE_ORDER
    }
    total = sum(normalized_scores.values())
    if not total:
        return {code: 0 for code in TASTE_TYPE_ORDER}

    raw = {
        code: normalized_scores[code] / total * 100
        for code in TASTE_TYPE_ORDER
    }
    rounded = {code: round(value, 1) for code, value in raw.items()}
    difference = round(100 - sum(rounded.values()), 1)
    if difference:
        largest = max(raw, key=raw.get)
        rounded[largest] = round(rounded[largest] + difference, 1)
    return rounded


def _axis_percentages(axis_scores, axis_definitions):
    rows = []
    for axis in axis_definitions:
        key = axis["key"]
        scores = axis_scores.get(key, {})
        left_score = max(float(scores.get("left", 0)), 0)
        right_score = max(float(scores.get("right", 0)), 0)
        total = left_score + right_score
        if total:
            left_percentage = round(left_score / total * 100, 1)
            right_percentage = round(100 - left_percentage, 1)
        else:
            left_percentage = 50.0
            right_percentage = 50.0
        rows.append({
            "key": key,
            "left_label": axis["left_label"],
            "right_label": axis["right_label"],
            "left_description": axis.get("left_description", ""),
            "right_description": axis.get("right_description", ""),
            "left_score": left_score,
            "right_score": right_score,
            "left_percentage": left_percentage,
            "right_percentage": right_percentage,
        })
    return rows


def _serialize_definition(definition):
    return {
        "code": definition.code,
        "name": definition.name,
        "base_type": definition.base_type,
        "subtitle": definition.subtitle,
        "summary": definition.summary,
        "description": definition.description,
        "keywords": definition.result_keywords,
        "character_concept": definition.character_concept,
    }


def get_taste_test_config():
    runtime_config = load_taste_config()
    config = TasteTestConfig.objects.filter(config_key="default").first()
    questions = list(TasteQuestion.objects.order_by("order_no"))
    result_types = {
        row.code: row
        for row in TasteTypeDefinition.objects.filter(code__in=TASTE_TYPE_ORDER)
    }
    runtime_questions = runtime_config.get("questions", [])
    if config is None or len(questions) != len(runtime_questions) or len(result_types) != 6:
        raise ValidationError(
            "취향 테스트 설정이 준비되지 않았습니다. sync_taste_config를 실행해 주세요."
        )

    return {
        "test_meta": config.test_meta,
        "total_questions": len(questions),
        "answer_options": runtime_config["test_meta"].get("answer_options", []),
        "axis_definitions": runtime_config.get("axis_definitions", []),
        "questions": [
            {
                "question_id": question.question_id,
                "order_no": question.order_no,
                "question_text": question.question_text,
                "options": next(
                    (
                        row.get("options", [])
                        for row in runtime_questions
                        if _question_key(row) == question.question_id
                    ),
                    [],
                ),
            }
            for question in questions
        ],
        "result_types": [
            {
                "code": code,
                "name": result_types[code].name,
                "base_type": result_types[code].base_type,
            }
            for code in TASTE_TYPE_ORDER
        ],
    }


def get_latest_taste_result(user):
    if not user or not user.is_authenticated:
        return {"result": None}

    latest_result = TasteResult.objects.filter(user=user).order_by("-created_at").first()
    if latest_result is None:
        return {"result": None}

    definition = TasteTypeDefinition.objects.filter(
        code=latest_result.result_type
    ).first()
    if definition is None:
        raise ValidationError("저장된 취향 결과의 유형 정보를 찾을 수 없습니다.")

    return {
        "result": {
            "saved": True,
            "result_id": latest_result.id,
            "created_at": latest_result.created_at,
            "result": _serialize_definition(definition),
            "scores": latest_result.score_data,
            "percentages": _percentages(latest_result.score_data),
            "axis_percentages": _axis_percentages(
                _extract_axis_scores(latest_result.score_data),
                load_taste_config().get("axis_definitions", []),
            ),
        }
    }


def _select_result_type(scores, representative_scores):
    highest_score = max(scores.values())
    tied_codes = [code for code in TASTE_TYPE_ORDER if scores[code] == highest_score]
    if len(tied_codes) == 1:
        return tied_codes[0]

    highest_representative_score = max(
        (representative_scores.get(code, 0) for code in tied_codes),
        default=0,
    )
    for code in TASTE_TYPE_ORDER:
        if (
            code in tied_codes
            and representative_scores.get(code, 0) == highest_representative_score
        ):
            return code
    return tied_codes[0]


@transaction.atomic
def evaluate_taste_test(user, answers):
    runtime_config = load_taste_config()
    runtime_questions = runtime_config.get("questions", [])
    questions = list(TasteQuestion.objects.order_by("order_no"))
    expected_ids = {question.question_id for question in questions}
    answers_by_id = {row["question_id"]: row["answer"] for row in answers}
    if len(questions) != len(runtime_questions) or set(answers_by_id) != expected_ids:
        raise ValidationError(
            {"answers": f"등록된 {len(runtime_questions)}개 질문에 모두 한 번씩 답변해 주세요."}
        )

    definitions = {
        row.code: row
        for row in TasteTypeDefinition.objects.filter(code__in=TASTE_TYPE_ORDER)
    }
    if len(definitions) != 6:
        raise ValidationError("취향 유형 설정이 준비되지 않았습니다.")

    scores = {code: 0.0 for code in TASTE_TYPE_ORDER}
    axis_definitions = runtime_config.get("axis_definitions", [])
    axis_scores = {
        axis["key"]: {"left": 0.0, "right": 0.0}
        for axis in axis_definitions
    }
    representative_questions = runtime_config.get(
        "calculation_policy", {}
    ).get("representative_questions", {})
    representative_scores = {code: 0.0 for code in TASTE_TYPE_ORDER}
    runtime_question_by_id = {
        _question_key(row): row
        for row in runtime_questions
    }

    for question_id, answer in answers_by_id.items():
        question_config = runtime_question_by_id.get(question_id)
        option = next(
            (row for row in question_config.get("options", []) if row.get("value") == answer),
            None,
        )
        if option is None:
            raise ValidationError(
                {"answers": f"{question_id}번 질문의 선택지가 유효하지 않습니다."}
            )
        for result_code, score in option.get("type_scores", {}).items():
            scores[result_code] += score
            if question_id in representative_questions.get(result_code, []):
                representative_scores[result_code] += score
        for axis_key, sides in option.get("axis_scores", {}).items():
            axis_scores.setdefault(axis_key, {"left": 0.0, "right": 0.0})
            axis_scores[axis_key]["left"] += sides.get("left", 0)
            axis_scores[axis_key]["right"] += sides.get("right", 0)

    result_code = _select_result_type(scores, representative_scores)
    definition = definitions[result_code]
    normalized_scores = {
        code: int(score) if float(score).is_integer() else score
        for code, score in scores.items()
    }
    normalized_axis_scores = {
        key: {
            side: int(score) if float(score).is_integer() else score
            for side, score in sides.items()
        }
        for key, sides in axis_scores.items()
    }
    score_data = {
        "type_scores": normalized_scores,
        "axis_scores": normalized_axis_scores,
    }
    percentages = _percentages(scores)
    axis_percentages = _axis_percentages(normalized_axis_scores, axis_definitions)

    saved_result = None
    is_authenticated = bool(user and user.is_authenticated)
    if is_authenticated:
        saved_result = TasteResult.objects.create(
            user=user,
            result_type=result_code,
            result_summary=definition.summary,
            score_data=score_data,
        )
        keywords = list(
            Keyword.objects.filter(
                name__in=definition.result_keywords,
                keyword_type=Keyword.KeywordType.COMMON,
            )
        )
        saved_result.keywords.set(keywords)
        UserKeyword.objects.filter(
            user=user,
            source_type=UserKeyword.SourceType.TEST,
        ).delete()
        UserKeyword.objects.bulk_create(
            [
                UserKeyword(
                    user=user,
                    keyword=keyword,
                    weight=1.0,
                    source_type=UserKeyword.SourceType.TEST,
                )
                for keyword in keywords
            ]
        )

    return {
        "saved": is_authenticated,
        "result_id": saved_result.id if saved_result else None,
        "result": _serialize_definition(definition),
        "scores": score_data,
        "percentages": percentages,
        "axis_percentages": axis_percentages,
    }

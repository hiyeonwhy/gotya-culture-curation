import json
import runpy

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from tastes.models import (
    Keyword,
    TasteQuestion,
    TasteScoreRule,
    TasteTestConfig,
    TasteTypeDefinition,
)


OUTPUT_DIR = settings.BASE_DIR.parent / "api_extract" / "taste_data" / "output"
CLEAN_SCRIPT_PATH = (
    settings.BASE_DIR.parent
    / "api_extract"
    / "taste_data"
    / "clean_taste_test_config.py"
)


def refresh_cleaned_files():
    if not CLEAN_SCRIPT_PATH.exists():
        raise CommandError(f"취향 정제 스크립트가 없습니다: {CLEAN_SCRIPT_PATH}")
    runpy.run_path(str(CLEAN_SCRIPT_PATH), run_name="__main__")


def load_json(name):
    path = OUTPUT_DIR / name
    if not path.exists():
        raise CommandError(
            f"취향 정제 파일이 없습니다: {path}. "
            "먼저 clean_taste_test_config.py를 실행하세요."
        )
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


class Command(BaseCommand):
    help = "정제된 취향 유형, 질문, 점수 규칙과 정책을 DB에 누적 동기화합니다."

    @transaction.atomic
    def handle(self, *args, **options):
        refresh_cleaned_files()
        type_rows = load_json("taste_types.json")
        question_rows = load_json("taste_questions.json")
        rule_rows = load_json("taste_score_rules.json")
        policy = load_json("taste_test_policy.json")
        recommendation_mapping = load_json("recommendation_db_mapping.json")
        active_type_codes = {row["code"] for row in type_rows}
        active_question_ids = {row["question_id"] for row in question_rows}
        active_rule_keys = {
            (row["question_id"], row["answer_value"])
            for row in rule_rows
        }

        type_by_code = {}
        for row in type_rows:
            code = row["code"]
            taste_type, _ = TasteTypeDefinition.objects.update_or_create(
                code=code,
                defaults={
                    "name": row["name"],
                    "base_type": row["base_type"],
                    "subtitle": row["subtitle"],
                    "summary": row["summary"],
                    "description": row["description"],
                    "keywords": row["keywords"],
                    "recommendation_guide": row["recommendation_guide"],
                    "recommendation_db_mapping": recommendation_mapping[code],
                    "result_keywords": row["result_keywords"],
                    "character_concept": row.get("character_concept"),
                },
            )
            type_by_code[code] = taste_type
            for keyword_name in row["result_keywords"]:
                Keyword.objects.get_or_create(
                    name=keyword_name,
                    keyword_type=Keyword.KeywordType.COMMON,
                )

        TasteScoreRule.objects.exclude(
            question__question_id__in=active_question_ids,
        ).delete()
        TasteScoreRule.objects.exclude(
            result_type_id__in=active_type_codes,
        ).delete()
        TasteQuestion.objects.exclude(question_id__in=active_question_ids).delete()
        TasteTypeDefinition.objects.exclude(code__in=active_type_codes).delete()

        question_by_external_id = {}
        for row in question_rows:
            question, _ = TasteQuestion.objects.update_or_create(
                question_id=row["question_id"],
                defaults={
                    "order_no": row["order_no"],
                    "question_text": row["question_text"],
                },
            )
            question_by_external_id[question.question_id] = question

        for row in rule_rows:
            question = question_by_external_id.get(row["question_id"])
            taste_type = type_by_code.get(row["result_code"])
            if question is None or taste_type is None:
                raise CommandError(f"점수 규칙 참조가 유효하지 않습니다: {row}")
            TasteScoreRule.objects.update_or_create(
                question=question,
                answer_value=row["answer_value"],
                defaults={
                    "result_type": taste_type,
                    "score": row["score"],
                },
            )

        stale_rules = [
            rule.id
            for rule in TasteScoreRule.objects.select_related("question")
            if (rule.question.question_id, rule.answer_value) not in active_rule_keys
        ]
        if stale_rules:
            TasteScoreRule.objects.filter(id__in=stale_rules).delete()

        TasteTestConfig.objects.update_or_create(
            config_key=policy["config_key"],
            defaults={
                "test_meta": policy["test_meta"],
                "calculation_policy": policy["calculation_policy"],
            },
        )

        self.stdout.write(self.style.SUCCESS(
            "취향 설정 동기화 완료: "
            f"유형 {len(type_by_code)}, 질문 {len(question_by_external_id)}, "
            f"점수 규칙 {len(rule_rows)}"
        ))

from django.conf import settings
from django.db import models


class TasteTypeDefinition(models.Model):
    code = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    base_type = models.CharField(max_length=100)
    subtitle = models.TextField()
    summary = models.TextField()
    description = models.JSONField(default=list)
    keywords = models.JSONField(default=list)
    recommendation_guide = models.JSONField(default=dict)
    recommendation_db_mapping = models.JSONField(default=dict)
    result_keywords = models.JSONField(default=list)
    character_concept = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "taste_type_definitions"
        ordering = ["code"]

    def __str__(self):
        return self.name


class TasteQuestion(models.Model):
    question_id = models.PositiveSmallIntegerField(unique=True)
    order_no = models.PositiveSmallIntegerField(unique=True)
    question_text = models.TextField()

    class Meta:
        db_table = "taste_questions"
        ordering = ["order_no"]

    def __str__(self):
        return f"{self.order_no}. {self.question_text}"


class TasteScoreRule(models.Model):
    question = models.ForeignKey(
        TasteQuestion,
        on_delete=models.CASCADE,
        related_name="score_rules",
    )
    answer_value = models.BooleanField()
    result_type = models.ForeignKey(
        TasteTypeDefinition,
        on_delete=models.CASCADE,
        related_name="score_rules",
    )
    score = models.FloatField()

    class Meta:
        db_table = "taste_score_rules"
        constraints = [
            models.UniqueConstraint(
                fields=["question", "answer_value"],
                name="unique_taste_question_answer_rule",
            )
        ]
        ordering = ["question__order_no", "answer_value"]


class TasteTestConfig(models.Model):
    config_key = models.CharField(max_length=50, unique=True, default="default")
    test_meta = models.JSONField(default=dict)
    calculation_policy = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "taste_test_configs"


class Keyword(models.Model):
    class KeywordType(models.TextChoices):
        MOVIE = "movie", "영화"
        BOOK = "book", "도서"
        CULTURE = "culture", "문화"
        COMMON = "common", "공통"

    name = models.CharField(max_length=100)
    keyword_type = models.CharField(max_length=20, choices=KeywordType.choices)

    class Meta:
        db_table = "keywords"
        constraints = [
            models.UniqueConstraint(
                fields=["name", "keyword_type"],
                name="unique_keyword_name_type",
            )
        ]
        ordering = ["keyword_type", "name"]

    def __str__(self):
        return f"{self.get_keyword_type_display()}: {self.name}"


class ContentItem(models.Model):
    class ContentType(models.TextChoices):
        MOVIE = "movie", "영화"
        BOOK = "book", "도서"
        CULTURE = "culture", "문화"

    content_type = models.CharField(max_length=10, choices=ContentType.choices)
    title = models.CharField(max_length=500)
    summary = models.TextField(null=True, blank=True)
    thumbnail_url = models.URLField(max_length=1000)
    source_url = models.URLField(max_length=1000, null=True, blank=True)
    is_adult = models.BooleanField(default=False)
    popularity_score = models.FloatField(null=True, blank=True)
    keywords = models.ManyToManyField(
        Keyword,
        through="ContentKeyword",
        related_name="content_items",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "content_items"
        ordering = ["-popularity_score", "-created_at"]
        indexes = [
            models.Index(fields=["content_type"], name="content_type_idx"),
            models.Index(fields=["title"], name="content_title_idx"),
        ]

    def __str__(self):
        return f"[{self.get_content_type_display()}] {self.title}"


class ContentKeyword(models.Model):
    content_item = models.ForeignKey(
        ContentItem,
        on_delete=models.CASCADE,
        related_name="content_keyword_links",
    )
    keyword = models.ForeignKey(
        Keyword,
        on_delete=models.CASCADE,
        related_name="content_keyword_links",
    )
    weight = models.FloatField(default=1.0)

    class Meta:
        db_table = "content_keywords"
        constraints = [
            models.UniqueConstraint(
                fields=["content_item", "keyword"],
                name="unique_content_keyword",
            )
        ]


class TasteResult(models.Model):
    class ResultType(models.TextChoices):
        TREND = "TREND", "유행 탑승형"
        MONGLE = "MONGLE", "마음 몽글형"
        WORLD = "WORLD", "세계관 과몰입형"
        KNOWLEDGE = "KNOWLEDGE", "지식 냠냠형"
        FESTIVAL = "FESTIVAL", "축제 팔랑귀형"
        TOGETHER = "TOGETHER", "같이보기 찰떡형"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="taste_results",
    )
    result_type = models.CharField(max_length=20, choices=ResultType.choices)
    result_summary = models.TextField()
    score_data = models.JSONField(default=dict)
    keywords = models.ManyToManyField(Keyword, related_name="taste_results", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "taste_results"
        ordering = ["-created_at"]


class UserKeyword(models.Model):
    class SourceType(models.TextChoices):
        TEST = "test", "취향 테스트"
        SELECTED = "selected", "직접 선택"
        FEEDBACK = "feedback", "콘텐츠 반응"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_keywords",
    )
    keyword = models.ForeignKey(
        Keyword,
        on_delete=models.CASCADE,
        related_name="user_keywords",
    )
    weight = models.FloatField(default=1.0)
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_keywords"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "keyword", "source_type"],
                name="unique_user_keyword_source",
            )
        ]


class Bookmark(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )
    content_item = models.ForeignKey(
        ContentItem,
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bookmarks"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "content_item"],
                name="unique_user_bookmark",
            )
        ]
        ordering = ["-created_at"]


class ContentFeedback(models.Model):
    class FeedbackType(models.TextChoices):
        LIKE = "like", "좋아요"
        DISLIKE = "dislike", "싫어요"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="content_feedbacks",
    )
    content_item = models.ForeignKey(
        ContentItem,
        on_delete=models.CASCADE,
        related_name="feedbacks",
    )
    feedback_type = models.CharField(max_length=10, choices=FeedbackType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "content_feedbacks"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "content_item"],
                name="unique_user_content_feedback",
            )
        ]
        ordering = ["-created_at"]

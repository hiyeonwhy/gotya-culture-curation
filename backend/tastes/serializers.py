from rest_framework import serializers

from .models import Bookmark, ContentFeedback, ContentItem, TasteResult


class RecommendationRequestSerializer(serializers.Serializer):
    taste_type = serializers.ChoiceField(
        choices=TasteResult.ResultType.choices,
        required=False,
        allow_null=True,
    )
    per_type = serializers.IntegerField(default=3, min_value=1, max_value=10)
    exclude_content_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        allow_empty=True,
        max_length=100,
    )


class TasteAnswerValueField(serializers.Field):
    def to_internal_value(self, data):
        if data is True:
            return "A"
        if data is False:
            return "B"
        if isinstance(data, str):
            normalized = data.strip().upper()
            if normalized in {"A", "B"}:
                return normalized
        raise serializers.ValidationError("답변은 A 또는 B 중 하나여야 합니다.")

    def to_representation(self, value):
        return value


class TasteAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField(min_value=1)
    answer = TasteAnswerValueField()


class TasteTestSubmissionSerializer(serializers.Serializer):
    answers = TasteAnswerSerializer(many=True, min_length=1, max_length=20)

    def validate_answers(self, answers):
        question_ids = [row["question_id"] for row in answers]
        if len(question_ids) != len(set(question_ids)):
            raise serializers.ValidationError("같은 질문에 중복으로 답변할 수 없습니다.")
        return answers


class BookmarkListSerializer(serializers.ModelSerializer):
    content_item_id = serializers.IntegerField(source="content_item.id", read_only=True)
    content_type = serializers.CharField(source="content_item.content_type", read_only=True)
    detail_id = serializers.SerializerMethodField()
    title = serializers.CharField(source="content_item.title", read_only=True)
    summary = serializers.CharField(source="content_item.summary", read_only=True)
    thumbnail_url = serializers.URLField(
        source="content_item.thumbnail_url",
        read_only=True,
    )
    source_url = serializers.URLField(source="content_item.source_url", read_only=True)
    popularity_score = serializers.FloatField(
        source="content_item.popularity_score",
        read_only=True,
    )
    metadata = serializers.SerializerMethodField()

    class Meta:
        model = Bookmark
        fields = (
            "id",
            "content_item_id",
            "content_type",
            "detail_id",
            "title",
            "summary",
            "thumbnail_url",
            "source_url",
            "popularity_score",
            "metadata",
            "created_at",
        )

    def get_detail_id(self, obj):
        content_item = obj.content_item
        content_type = content_item.content_type
        if content_type == ContentItem.ContentType.MOVIE:
            detail = getattr(content_item, "movie_detail", None)
            return detail.tmdb_id if detail else None
        if content_type == ContentItem.ContentType.BOOK:
            detail = getattr(content_item, "book_detail", None)
            return detail.item_id if detail else None
        if content_type == ContentItem.ContentType.CULTURE:
            detail = getattr(content_item, "culture_event", None)
            return detail.seq if detail else None
        return None

    def get_metadata(self, obj):
        return get_content_metadata(obj.content_item)


class BookmarkToggleSerializer(serializers.Serializer):
    content_item_id = serializers.IntegerField(min_value=1)

    def validate_content_item_id(self, value):
        if not ContentItem.objects.filter(id=value).exists():
            raise serializers.ValidationError("존재하지 않는 콘텐츠입니다.")
        return value


class BookmarkStatusSerializer(serializers.Serializer):
    content_item_id = serializers.IntegerField(min_value=1)


class ContentFeedbackSerializer(serializers.Serializer):
    content_item_id = serializers.IntegerField(min_value=1)
    feedback_type = serializers.ChoiceField(choices=ContentFeedback.FeedbackType.values)

    def validate_content_item_id(self, value):
        if not ContentItem.objects.filter(id=value).exists():
            raise serializers.ValidationError("존재하지 않는 콘텐츠입니다.")
        return value


class ContentFeedbackStatusSerializer(serializers.Serializer):
    content_item_id = serializers.IntegerField(min_value=1)


class ContentFeedbackListSerializer(serializers.ModelSerializer):
    content_item_id = serializers.IntegerField(source="content_item.id", read_only=True)
    content_type = serializers.CharField(source="content_item.content_type", read_only=True)
    detail_id = serializers.SerializerMethodField()
    title = serializers.CharField(source="content_item.title", read_only=True)
    summary = serializers.CharField(source="content_item.summary", read_only=True)
    thumbnail_url = serializers.URLField(
        source="content_item.thumbnail_url",
        read_only=True,
    )
    source_url = serializers.URLField(source="content_item.source_url", read_only=True)
    popularity_score = serializers.FloatField(
        source="content_item.popularity_score",
        read_only=True,
    )
    metadata = serializers.SerializerMethodField()

    class Meta:
        model = ContentFeedback
        fields = (
            "id",
            "content_item_id",
            "content_type",
            "detail_id",
            "title",
            "summary",
            "thumbnail_url",
            "source_url",
            "popularity_score",
            "feedback_type",
            "metadata",
            "created_at",
        )

    def get_detail_id(self, obj):
        content_item = obj.content_item
        content_type = content_item.content_type
        if content_type == ContentItem.ContentType.MOVIE:
            detail = getattr(content_item, "movie_detail", None)
            return detail.tmdb_id if detail else None
        if content_type == ContentItem.ContentType.BOOK:
            detail = getattr(content_item, "book_detail", None)
            return detail.item_id if detail else None
        if content_type == ContentItem.ContentType.CULTURE:
            detail = getattr(content_item, "culture_event", None)
            return detail.seq if detail else None
        return None

    def get_metadata(self, obj):
        return get_content_metadata(obj.content_item)


def get_content_metadata(content_item):
    content_type = content_item.content_type
    if content_type == ContentItem.ContentType.MOVIE:
        detail = getattr(content_item, "movie_detail", None)
        return {
            "genres": [
                genre.name
                for genre in detail.genres.all()
            ] if detail else [],
            "release_date": detail.release_date.isoformat() if detail else None,
        }
    if content_type == ContentItem.ContentType.BOOK:
        detail = getattr(content_item, "book_detail", None)
        return {
            "categories": [
                category.name
                for category in detail.categories.all()
            ] if detail else [],
            "pub_date": detail.pub_date.isoformat() if detail else None,
        }
    if content_type == ContentItem.ContentType.CULTURE:
        detail = getattr(content_item, "culture_event", None)
        return {
            "main_category": detail.main_category if detail else None,
            "sub_category": detail.sub_category if detail else None,
            "start_date": detail.start_date.isoformat() if detail else None,
            "end_date": detail.end_date.isoformat() if detail else None,
        }
    return {}

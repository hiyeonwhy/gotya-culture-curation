from collections import defaultdict
from random import choice

from tastes.models import ContentFeedback, TasteResult, UserKeyword

from .recommendation_mapping import TASTE_LABELS, get_ai_taste_guide


def build_user_profile(user, requested_taste_type=None):
    is_authenticated = bool(user and user.is_authenticated)
    latest_result = None
    if is_authenticated:
        latest_result = (
            TasteResult.objects.filter(user=user)
            .prefetch_related("keywords")
            .order_by("-created_at")
            .first()
        )

    if requested_taste_type:
        taste_type = requested_taste_type
        selection_source = "selected"
    elif latest_result:
        taste_type = latest_result.result_type
        selection_source = "taste_result"
    else:
        taste_type = choice(list(TASTE_LABELS))
        selection_source = "random"

    keyword_weights = defaultdict(float)
    if is_authenticated:
        user_keywords = UserKeyword.objects.filter(user=user).select_related("keyword")
        for user_keyword in user_keywords:
            keyword_weights[user_keyword.keyword.name] += user_keyword.weight

    if latest_result:
        for keyword in latest_result.keywords.all():
            keyword_weights[keyword.name] += 1.0

    feedback_rows = []
    if is_authenticated:
        feedback_rows = list(
            ContentFeedback.objects.filter(user=user).select_related("content_item")
        )
    liked_titles = [
        row.content_item.title
        for row in feedback_rows
        if row.feedback_type == ContentFeedback.FeedbackType.LIKE
    ][:10]
    disliked_content_ids = {
        row.content_item_id
        for row in feedback_rows
        if row.feedback_type == ContentFeedback.FeedbackType.DISLIKE
    }
    bookmarked_titles = []
    if is_authenticated:
        bookmarked_titles = list(
            user.bookmarks.select_related("content_item")
            .values_list("content_item__title", flat=True)[:10]
        )

    return {
        "is_authenticated": is_authenticated,
        "selection_source": selection_source,
        "taste_type": taste_type,
        "taste_label": TASTE_LABELS[taste_type],
        "result_taste_type": latest_result.result_type if latest_result else None,
        "result_taste_label": (
            TASTE_LABELS[latest_result.result_type] if latest_result else None
        ),
        "taste_guide": get_ai_taste_guide(taste_type),
        "score_data": latest_result.score_data if latest_result else {},
        "keywords": [
            {"name": name, "weight": round(weight, 2)}
            for name, weight in sorted(
                keyword_weights.items(), key=lambda item: (-item[1], item[0])
            )[:20]
        ],
        "liked_titles": liked_titles,
        "bookmarked_titles": bookmarked_titles,
        "disliked_content_ids": disliked_content_ids,
    }

from django.urls import path

from .views import (
    BookmarkListView,
    BookmarkStatusView,
    BookmarkToggleView,
    ContentFeedbackStatusView,
    ContentFeedbackView,
    DislikedContentListView,
    GenerateRecommendationView,
    RecommendationPreviewView,
    TasteTestConfigView,
    LatestTasteTestResultView,
    TasteTestResultView,
)


app_name = "tastes"

urlpatterns = [
    path("bookmarks/", BookmarkListView.as_view(), name="bookmark-list"),
    path("bookmarks/status/", BookmarkStatusView.as_view(), name="bookmark-status"),
    path("bookmarks/toggle/", BookmarkToggleView.as_view(), name="bookmark-toggle"),
    path("feedback/status/", ContentFeedbackStatusView.as_view(), name="feedback-status"),
    path("feedback/", ContentFeedbackView.as_view(), name="feedback"),
    path("feedback/dislikes/", DislikedContentListView.as_view(), name="feedback-dislikes"),
    path("test/config/", TasteTestConfigView.as_view(), name="taste-test-config"),
    path(
        "test/results/latest/",
        LatestTasteTestResultView.as_view(),
        name="taste-test-latest-result",
    ),
    path("test/results/", TasteTestResultView.as_view(), name="taste-test-result"),
    path(
        "recommendations/preview/",
        RecommendationPreviewView.as_view(),
        name="recommendation-preview",
    ),
    path(
        "recommendations/generate/",
        GenerateRecommendationView.as_view(),
        name="recommendation-generate",
    ),
]

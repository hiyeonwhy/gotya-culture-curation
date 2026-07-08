from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ContentFeedback, ContentItem
from .serializers import (
    BookmarkListSerializer,
    BookmarkStatusSerializer,
    BookmarkToggleSerializer,
    ContentFeedbackListSerializer,
    ContentFeedbackSerializer,
    ContentFeedbackStatusSerializer,
    RecommendationRequestSerializer,
    TasteTestSubmissionSerializer,
)
from .services.recommendation_service import (
    generate_database_recommendations,
    generate_recommendations,
)
from .services.taste_test_service import (
    evaluate_taste_test,
    get_latest_taste_result,
    get_taste_test_config,
)


class BookmarkPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 30


class TasteTestConfigView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(get_taste_test_config(), status=status.HTTP_200_OK)


class TasteTestResultView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TasteTestSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = evaluate_taste_test(
            user=request.user if request.user.is_authenticated else None,
            answers=serializer.validated_data["answers"],
        )
        return Response(result, status=status.HTTP_201_CREATED)


class LatestTasteTestResultView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        result = get_latest_taste_result(
            request.user if request.user.is_authenticated else None
        )
        return Response(result, status=status.HTTP_200_OK)


class RecommendationPreviewView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RecommendationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = generate_database_recommendations(
            user=request.user if request.user.is_authenticated else None,
            taste_type=serializer.validated_data.get("taste_type"),
            per_type=serializer.validated_data["per_type"],
            exclude_content_ids=serializer.validated_data.get("exclude_content_ids", []),
        )
        return Response(result, status=status.HTTP_200_OK)


class GenerateRecommendationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RecommendationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = generate_recommendations(
            user=request.user if request.user.is_authenticated else None,
            taste_type=serializer.validated_data.get("taste_type"),
            per_type=serializer.validated_data["per_type"],
            exclude_content_ids=serializer.validated_data.get("exclude_content_ids", []),
        )
        return Response(result, status=status.HTTP_200_OK)


class BookmarkListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = BookmarkPagination

    def get(self, request):
        content_type = request.query_params.get("content_type")
        queryset = request.user.bookmarks.select_related(
            "content_item",
            "content_item__movie_detail",
            "content_item__book_detail",
            "content_item__culture_event",
        ).prefetch_related(
            "content_item__movie_detail__genres",
            "content_item__book_detail__categories",
        )

        if content_type in ContentItem.ContentType.values:
            queryset = queryset.filter(content_item__content_type=content_type)

        queryset = queryset.order_by("-created_at", "-id")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = BookmarkListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class BookmarkToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BookmarkToggleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        content_item_id = serializer.validated_data["content_item_id"]

        bookmark = request.user.bookmarks.filter(content_item_id=content_item_id).first()
        if bookmark is not None:
            bookmark.delete()
            return Response({"bookmarked": False}, status=status.HTTP_200_OK)

        bookmark = request.user.bookmarks.create(content_item_id=content_item_id)
        return Response({"bookmarked": True, "bookmark_id": bookmark.id}, status=status.HTTP_201_CREATED)


class BookmarkStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = BookmarkStatusSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        content_item_id = serializer.validated_data["content_item_id"]
        bookmarked = request.user.bookmarks.filter(content_item_id=content_item_id).exists()
        return Response({"bookmarked": bookmarked}, status=status.HTTP_200_OK)


class DislikedContentListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = BookmarkPagination

    def get(self, request):
        content_type = request.query_params.get("content_type")
        queryset = request.user.content_feedbacks.select_related(
            "content_item",
            "content_item__movie_detail",
            "content_item__book_detail",
            "content_item__culture_event",
        ).prefetch_related(
            "content_item__movie_detail__genres",
            "content_item__book_detail__categories",
        ).filter(
            feedback_type=ContentFeedback.FeedbackType.DISLIKE,
        )

        if content_type in ContentItem.ContentType.values:
            queryset = queryset.filter(content_item__content_type=content_type)

        queryset = queryset.order_by("-created_at", "-id")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = ContentFeedbackListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class ContentFeedbackStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        serializer = ContentFeedbackStatusSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        content_item_id = serializer.validated_data["content_item_id"]
        like_count = ContentFeedback.objects.filter(
            content_item_id=content_item_id,
            feedback_type=ContentFeedback.FeedbackType.LIKE,
        ).count()
        user_feedback = None
        if request.user.is_authenticated:
            user_feedback = (
                request.user.content_feedbacks
                .filter(content_item_id=content_item_id)
                .values_list("feedback_type", flat=True)
                .first()
            )
        return Response(
            {"like_count": like_count, "feedback_type": user_feedback},
            status=status.HTTP_200_OK,
        )


class ContentFeedbackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ContentFeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        content_item_id = serializer.validated_data["content_item_id"]
        feedback_type = serializer.validated_data["feedback_type"]

        feedback = request.user.content_feedbacks.filter(
            content_item_id=content_item_id,
        ).first()

        if feedback and feedback.feedback_type == feedback_type:
            feedback.delete()
            current_feedback = None
        elif feedback:
            feedback.feedback_type = feedback_type
            feedback.save(update_fields=["feedback_type"])
            current_feedback = feedback.feedback_type
        else:
            feedback = request.user.content_feedbacks.create(
                content_item_id=content_item_id,
                feedback_type=feedback_type,
            )
            current_feedback = feedback.feedback_type

        like_count = ContentFeedback.objects.filter(
            content_item_id=content_item_id,
            feedback_type=ContentFeedback.FeedbackType.LIKE,
        ).count()
        return Response(
            {"like_count": like_count, "feedback_type": current_feedback},
            status=status.HTTP_200_OK,
        )

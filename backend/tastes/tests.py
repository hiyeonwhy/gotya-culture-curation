from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import override_settings
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from books.models import BookCategory, BookCategoryMap, BookDetail
from cultures.models import CultureEvent, Place
from movies.models import GenreName, MovieDetail, MovieGenre
from tastes.models import (
    Bookmark,
    ContentFeedback,
    ContentItem,
    TasteResult,
    UserKeyword,
)


User = get_user_model()


class TasteTestApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("sync_taste_config", verbosity=0)
        cls.user = User.objects.create_user(
            login_id="taste-user",
            password="StrongPass123!",
            nickname="취향사용자",
        )
        cls.token = Token.objects.create(user=cls.user)

    def answer_payload(self, value="A"):
        return {
            "answers": [
                {"question_id": question_id, "answer": value}
                for question_id in range(1, 14)
            ]
        }

    def test_config_returns_thirteen_questions_and_six_result_types(self):
        response = self.client.get("/api/tastes/test/config/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_questions"], 13)
        self.assertEqual(len(response.data["questions"]), 13)
        self.assertEqual(len(response.data["result_types"]), 6)
        self.assertEqual(len(response.data["axis_definitions"]), 4)
        self.assertEqual(len(response.data["questions"][0]["options"]), 2)

    def test_guest_can_complete_test_without_saving_result(self):
        response = self.client.post(
            "/api/tastes/test/results/",
            self.answer_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data["saved"])
        self.assertIsNone(response.data["result_id"])
        self.assertEqual(response.data["result"]["code"], "FESTIVAL")
        self.assertAlmostEqual(sum(response.data["percentages"].values()), 100)
        self.assertEqual(len(response.data["axis_percentages"]), 4)
        self.assertEqual(TasteResult.objects.count(), 0)

    def test_authenticated_result_and_test_keywords_are_saved(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        response = self.client.post(
            "/api/tastes/test/results/",
            self.answer_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["saved"])
        self.assertTrue(TasteResult.objects.filter(user=self.user).exists())
        self.assertTrue(
            UserKeyword.objects.filter(
                user=self.user,
                source_type=UserKeyword.SourceType.TEST,
            ).exists()
        )

        latest_response = self.client.get("/api/tastes/test/results/latest/")
        self.assertEqual(latest_response.status_code, status.HTTP_200_OK)
        self.assertEqual(latest_response.data["result"]["result"]["code"], "FESTIVAL")
        self.assertAlmostEqual(
            sum(latest_response.data["result"]["percentages"].values()),
            100,
        )
        self.assertEqual(len(latest_response.data["result"]["axis_percentages"]), 4)

    def test_guest_latest_result_is_empty(self):
        response = self.client.get("/api/tastes/test/results/latest/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["result"])

    def test_all_thirteen_questions_are_required(self):
        payload = self.answer_payload()
        payload["answers"].pop()

        response = self.client.post(
            "/api/tastes/test/results/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class BookmarkApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            login_id="bookmark-user",
            password="StrongPass123!",
            nickname="찜사용자",
        )
        self.other_user = User.objects.create_user(
            login_id="other-bookmark-user",
            password="StrongPass123!",
            nickname="다른찜사용자",
        )
        self.token = Token.objects.create(user=self.user)
        self.book = self.create_content("book", "찜한 도서", 30)
        self.movie = self.create_content("movie", "찜한 영화", 20)
        self.other_book = self.create_content("book", "다른 사람 도서", 10)
        Bookmark.objects.create(user=self.user, content_item=self.book)
        Bookmark.objects.create(user=self.user, content_item=self.movie)
        Bookmark.objects.create(user=self.other_user, content_item=self.other_book)

    def create_content(self, content_type, title, popularity):
        return ContentItem.objects.create(
            content_type=content_type,
            title=title,
            summary=f"{title} 요약",
            thumbnail_url="https://example.com/thumb.jpg",
            source_url="https://example.com/detail",
            popularity_score=popularity,
        )

    def test_bookmark_list_requires_login(self):
        response = self.client.get("/api/tastes/bookmarks/")

        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_bookmark_list_returns_only_current_user_bookmarks(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

        response = self.client.get("/api/tastes/bookmarks/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        titles = {row["title"] for row in response.data["results"]}
        self.assertEqual(titles, {"찜한 도서", "찜한 영화"})

    def test_bookmark_list_can_filter_by_content_type(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

        response = self.client.get("/api/tastes/bookmarks/?content_type=book")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["content_type"], "book")


@override_settings(GMS_API_URL="", GMS_API_KEY="", GMS_CANDIDATES_PER_TYPE=5)
class RecommendationApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            login_id="recommend-user",
            password="StrongPass123!",
            nickname="추천사용자",
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        TasteResult.objects.create(
            user=self.user,
            result_type=TasteResult.ResultType.KNOWLEDGE,
            result_summary="지식을 얻는 콘텐츠를 선호합니다.",
            score_data={"KNOWLEDGE": 8},
        )
        self.movie = self.create_movie()
        self.book = self.create_book()
        self.culture = self.create_culture()

    def create_content(self, content_type, title, popularity=10):
        return ContentItem.objects.create(
            content_type=content_type,
            title=title,
            summary=f"{title} 설명",
            thumbnail_url="https://example.com/image.jpg",
            source_url="https://example.com/content",
            popularity_score=popularity,
        )

    def create_movie(self):
        content = self.create_content("movie", "역사 다큐멘터리")
        movie = MovieDetail.objects.create(
            content_item=content,
            tmdb_id=1001,
            original_title="History Documentary",
            original_language="ko",
            poster_path="/poster.jpg",
            release_date=date.today(),
            vote_average=8.5,
            popularity=100,
        )
        genre = GenreName.objects.create(tmdb_genre_id=99, name="다큐멘터리")
        MovieGenre.objects.create(movie_detail=movie, genre_name=genre)
        return movie

    def create_book(self):
        content = self.create_content("book", "인문학 도서")
        book = BookDetail.objects.create(
            content_item=content,
            item_id=2001,
            author="저자",
            publisher="출판사",
            pub_date=date.today(),
            sales_point=100,
        )
        category = BookCategory.objects.create(
            aladin_category_id=656,
            name="인문학",
        )
        BookCategoryMap.objects.create(book_detail=book, category=category)
        return book

    def create_culture(self):
        content = self.create_content("culture", "지식 전시")
        place = Place.objects.create(place_name="전시장", address="광주광역시")
        return CultureEvent.objects.create(
            content_item=content,
            place=place,
            seq="culture-1",
            main_category="전시",
            sub_category="전시",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
        )

    def test_guest_can_generate_recommendations_with_selected_taste(self):
        self.client.credentials()
        response = self.client.post(
            "/api/tastes/recommendations/generate/",
            {"taste_type": "KNOWLEDGE", "per_type": 1},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["profile"]["is_authenticated"])
        self.assertEqual(response.data["profile"]["selection_source"], "selected")
        self.assertEqual(response.data["profile"]["taste_type"], "KNOWLEDGE")

    def test_guest_without_selected_taste_uses_random_taste(self):
        self.client.credentials()
        response = self.client.post(
            "/api/tastes/recommendations/generate/",
            {"per_type": 1},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["profile"]["selection_source"], "random")
        self.assertIn(
            response.data["profile"]["taste_type"],
            TasteResult.ResultType.values,
        )

    def test_database_fallback_returns_each_content_type(self):
        response = self.client.post(
            "/api/tastes/recommendations/generate/",
            {"per_type": 1},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["source"], "database_fallback")
        self.assertEqual(response.data["profile"]["taste_type"], "KNOWLEDGE")
        self.assertTrue(response.data["profile"]["is_authenticated"])
        self.assertEqual(
            response.data["profile"]["result_taste_label"],
            "지식 냠냠형",
        )
        self.assertEqual(
            response.data["profile"]["score_percentages"]["KNOWLEDGE"],
            100,
        )
        for content_type in ("movie", "book", "culture"):
            self.assertEqual(len(response.data["recommendations"][content_type]), 1)

    @patch("tastes.views.generate_recommendations")
    def test_preview_returns_database_result_without_calling_gms_service(
        self,
        mock_generate,
    ):
        response = self.client.post(
            "/api/tastes/recommendations/preview/",
            {"per_type": 1},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["source"], "database_preview")
        mock_generate.assert_not_called()
        for content_type in ("movie", "book", "culture"):
            self.assertEqual(len(response.data["recommendations"][content_type]), 1)

    @patch("tastes.services.recommendation_service.GMSClient.generate")
    def test_gms_ids_are_mapped_to_database_contents(self, mock_generate):
        mock_generate.return_value = {
            "recommendations": {
                "movie": [{
                    "content_item_id": self.movie.content_item_id,
                    "reason": "관심 장르와 잘 맞습니다.",
                }],
                "book": [{
                    "content_item_id": self.book.content_item_id,
                    "reason": "인문학 취향과 잘 맞습니다.",
                }],
                "culture": [{
                    "content_item_id": self.culture.content_item_id,
                    "reason": "전시 취향과 잘 맞습니다.",
                }],
            }
        }

        response = self.client.post(
            "/api/tastes/recommendations/generate/",
            {"per_type": 1},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["source"], "gms")
        self.assertEqual(
            response.data["recommendations"]["movie"][0]["content_item_id"],
            self.movie.content_item_id,
        )

    @patch("tastes.services.recommendation_service.GMSClient.generate")
    def test_hallucinated_id_is_replaced_with_fallback(self, mock_generate):
        mock_generate.return_value = {
            "recommendations": {
                "movie": [{"content_item_id": 999999, "reason": "없는 콘텐츠"}],
                "book": [],
                "culture": [],
            }
        }

        response = self.client.post(
            "/api/tastes/recommendations/generate/",
            {"per_type": 1},
            format="json",
        )

        self.assertEqual(
            response.data["recommendations"]["movie"][0]["content_item_id"],
            self.movie.content_item_id,
        )

    @patch("tastes.services.recommendation_service.GMSClient.generate")
    def test_compact_gms_id_array_is_mapped_to_database_contents(self, mock_generate):
        mock_generate.return_value = {
            "recommendations": {
                "movie": [self.movie.content_item_id],
                "book": [self.book.content_item_id],
                "culture": [self.culture.content_item_id],
            }
        }

        response = self.client.post(
            "/api/tastes/recommendations/generate/",
            {"per_type": 1},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["recommendations"]["movie"][0]["content_item_id"],
            self.movie.content_item_id,
        )

    @patch("tastes.services.recommendation_service.GMSClient.generate")
    def test_large_result_asks_gms_for_at_most_three_per_type(self, mock_generate):
        mock_generate.return_value = {"recommendations": {}}

        response = self.client.post(
            "/api/tastes/recommendations/generate/",
            {"per_type": 10},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(mock_generate.call_args.args[2], 3)

    @patch("tastes.services.recommendation_service.GMSClient.generate")
    def test_same_recommendation_request_reuses_cached_gms_result(self, mock_generate):
        mock_generate.return_value = {"recommendations": {}}
        payload = {"taste_type": "KNOWLEDGE", "per_type": 1}

        first = self.client.post(
            "/api/tastes/recommendations/generate/",
            payload,
            format="json",
        )
        second = self.client.post(
            "/api/tastes/recommendations/generate/",
            payload,
            format="json",
        )

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertFalse(first.data["cached"])
        self.assertTrue(second.data["cached"])
        self.assertEqual(mock_generate.call_count, 1)

    def test_disliked_content_is_excluded(self):
        ContentFeedback.objects.create(
            user=self.user,
            content_item=self.movie.content_item,
            feedback_type=ContentFeedback.FeedbackType.DISLIKE,
        )

        response = self.client.post(
            "/api/tastes/recommendations/generate/",
            {"per_type": 1},
            format="json",
        )

        self.assertEqual(response.data["recommendations"]["movie"], [])

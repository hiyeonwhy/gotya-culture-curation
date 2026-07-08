from datetime import date

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from movies.models import GenreName, MovieDetail, MovieGenre
from tastes.models import ContentItem


@override_settings(ROOT_URLCONF="movies.urls")
class MovieQueryAPITests(APITestCase):
    def setUp(self):
        content = ContentItem.objects.create(
            content_type=ContentItem.ContentType.MOVIE,
            title="테스트 영화",
            summary="우주 모험 이야기",
            thumbnail_url="https://example.com/movie.jpg",
            source_url="https://example.com/movie",
            popularity_score=99,
        )
        self.movie = MovieDetail.objects.create(
            content_item=content,
            tmdb_id=101,
            original_title="Test Movie",
            original_language="ko",
            poster_path="/movie.jpg",
            release_date=date(2026, 1, 1),
            vote_average=8.5,
            vote_count=100,
            popularity=99,
        )
        genre = GenreName.objects.create(tmdb_genre_id=12, name="모험")
        MovieGenre.objects.create(movie_detail=self.movie, genre_name=genre)

    def test_list_filters_by_genre_and_contains_content_id(self):
        response = self.client.get("/", {"genre": "12"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["content_id"], self.movie.content_item_id)

    def test_detail_uses_tmdb_id(self):
        response = self.client.get("/101/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["tmdb_id"], 101)
        self.assertEqual(response.data["genres"][0]["name"], "모험")

    def test_page_size_is_limited_to_fifty(self):
        response = self.client.get("/", {"page_size": 1000})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)

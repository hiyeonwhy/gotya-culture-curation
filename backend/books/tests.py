from datetime import date

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from books.models import BookCategory, BookCategoryMap, BookDetail
from tastes.models import ContentItem


@override_settings(ROOT_URLCONF="books.urls")
class BookQueryAPITests(APITestCase):
    def setUp(self):
        content = ContentItem.objects.create(
            content_type=ContentItem.ContentType.BOOK,
            title="테스트 도서",
            summary="책 소개",
            thumbnail_url="https://example.com/book.jpg",
            source_url="https://example.com/book",
            popularity_score=500,
        )
        self.book = BookDetail.objects.create(
            content_item=content,
            item_id=202,
            author="작가",
            publisher="출판사",
            pub_date=date(2026, 2, 1),
            sales_point=500,
            customer_review_rank=9,
            has_ebook=True,
        )
        category = BookCategory.objects.create(
            aladin_category_id=2551,
            name="만화/라이트노벨",
        )
        BookCategoryMap.objects.create(book_detail=self.book, category=category)

    def test_list_filters_by_category_and_ebook(self):
        response = self.client.get(
            "/",
            {"category": "2551", "has_ebook": "true"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertTrue(response.data["results"][0]["has_ebook"])

    def test_detail_uses_aladin_item_id(self):
        response = self.client.get("/202/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["item_id"], 202)
        self.assertEqual(response.data["content_id"], self.book.content_item_id)

    def test_invalid_boolean_filter_returns_bad_request(self):
        response = self.client.get("/", {"has_ebook": "yes"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_aladin_thumbnail_uses_high_resolution_cover(self):
        self.book.content_item.thumbnail_url = (
            "https://image.aladin.co.kr/product/1/2/coversum/test.jpg"
        )
        self.book.content_item.save(update_fields=["thumbnail_url"])

        response = self.client.get("/202/")

        self.assertEqual(
            response.data["thumbnail_url"],
            "https://image.aladin.co.kr/product/1/2/cover500/test.jpg",
        )

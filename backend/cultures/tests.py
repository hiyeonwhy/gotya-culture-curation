from datetime import timedelta

from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from cultures.models import CultureEvent, Place
from tastes.models import ContentItem


@override_settings(ROOT_URLCONF="cultures.urls")
class CultureQueryAPITests(APITestCase):
    def setUp(self):
        today = timezone.localdate()
        place = Place.objects.create(
            place_name="테스트 공연장",
            area="서울",
            sigungu="종로구",
            address="서울특별시 종로구",
            longitude=126.9,
            latitude=37.5,
        )
        content = ContentItem.objects.create(
            content_type=ContentItem.ContentType.CULTURE,
            title="테스트 공연",
            thumbnail_url="https://example.com/culture.jpg",
            source_url="https://example.com/culture",
        )
        self.event = CultureEvent.objects.create(
            content_item=content,
            place=place,
            seq="CULTURE-1",
            main_category="공연",
            sub_category="연극",
            start_date=today - timedelta(days=1),
            end_date=today + timedelta(days=1),
            is_map_available=True,
        )

    def test_list_filters_by_region_ongoing_and_map(self):
        response = self.client.get(
            "/",
            {"area": "서울", "ongoing": "true", "map_only": "true"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["place"]["sigungu"], "종로구")

    def test_detail_uses_seq(self):
        response = self.client.get("/CULTURE-1/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["seq"], "CULTURE-1")
        self.assertEqual(response.data["content_id"], self.event.content_item_id)

    def test_invalid_boolean_filter_returns_bad_request(self):
        response = self.client.get("/", {"map_only": "yes"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_region_summary_returns_map_event_counts(self):
        response = self.client.get("/regions/summary/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [{"area": "서울", "count": 1}])

    def test_map_only_excludes_categories_outside_map_scope(self):
        self.event.main_category = "교육·체험"
        self.event.save(update_fields=["main_category"])

        response = self.client.get("/", {"map_only": "true"})
        summary_response = self.client.get("/regions/summary/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(summary_response.data, [])

    def test_map_scope_can_return_event_without_coordinates(self):
        self.event.main_category = "축제·행사"
        self.event.is_map_available = False
        self.event.place.latitude = None
        self.event.place.longitude = None
        self.event.place.save(update_fields=["latitude", "longitude"])
        self.event.save(update_fields=["main_category", "is_map_available"])

        response = self.client.get("/", {"map_scope": "true", "area": "서울"})
        summary_response = self.client.get(
            "/regions/summary/", {"main_category": "축제·행사"}
        )

        self.assertEqual(response.data["count"], 1)
        self.assertEqual(summary_response.data, [{"area": "서울", "count": 1}])

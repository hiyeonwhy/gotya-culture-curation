import json
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cultures.models import CultureEvent, Place
from tastes.models import ContentItem


OUTPUT_DIR = settings.BASE_DIR.parent / "api_extract" / "culture_data" / "output"
DATA_FILES = (
    "performances.json",
    "exhibitions.json",
    "education_experience.json",
    "festivals_events.json",
    "family_children.json",
    "sports_other.json",
)


def load_rows():
    rows = []
    for name in DATA_FILES:
        path = OUTPUT_DIR / name
        if not path.exists():
            raise CommandError(f"정제 파일이 없습니다: {path}")
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, list):
            raise CommandError(f"문화 정제 파일이 배열이 아닙니다: {path}")
        rows.extend(data)
    return rows


def parse_date(value):
    return datetime.strptime(value, "%Y%m%d").date()


class Command(BaseCommand):
    help = "정제된 문화행사 JSON을 DB에 생성 또는 갱신합니다."

    @transaction.atomic
    def handle(self, *args, **options):
        rows = load_rows()

        imported_sequences = {str(row["seq"]) for row in rows}
        existing = {
            event.seq: event
            for event in CultureEvent.objects.select_related("content_item", "place").all()
            if event.seq in imported_sequences
        }
        place_cache = {}
        created_count = 0
        updated_count = 0

        for row in rows:
            place_key = (
                row.get("place"),
                row.get("address"),
                row.get("longitude"),
                row.get("latitude"),
            )
            place = place_cache.get(place_key)
            if place is None:
                place, _ = Place.objects.get_or_create(
                    place_name=row.get("place"),
                    address=row.get("address"),
                    defaults={
                        "area": row.get("area"),
                        "sigungu": row.get("sigungu"),
                        "longitude": row.get("longitude"),
                        "latitude": row.get("latitude"),
                    },
                )
                changed = False
                for field in ("area", "sigungu", "longitude", "latitude"):
                    value = row.get(field)
                    if getattr(place, field) != value:
                        setattr(place, field, value)
                        changed = True
                if changed:
                    place.save(update_fields=["area", "sigungu", "longitude", "latitude"])
                place_cache[place_key] = place

            seq = str(row["seq"])
            content_defaults = {
                "content_type": ContentItem.ContentType.CULTURE,
                "title": row["name"],
                "summary": None,
                "thumbnail_url": row["thumbnail"],
                "source_url": row.get("url"),
                "is_adult": False,
                "popularity_score": None,
            }
            detail_defaults = {
                "place": place,
                "main_category": row["cultureMainCategory"],
                "sub_category": row["cultureSubCategory"],
                "realm_code": row.get("realmCode"),
                "realm_name": row.get("realmName"),
                "start_date": parse_date(row["startDate"]),
                "end_date": parse_date(row["endDate"]),
                "price": row.get("price"),
                "contact": row.get("phone"),
                "is_map_available": bool(row.get("isMapAvailable", False)),
            }

            event = existing.get(seq)
            if event is None:
                content_item = ContentItem.objects.create(**content_defaults)
                CultureEvent.objects.create(
                    content_item=content_item,
                    seq=seq,
                    **detail_defaults,
                )
                created_count += 1
            else:
                for field, value in content_defaults.items():
                    setattr(event.content_item, field, value)
                event.content_item.save(update_fields=[
                    *content_defaults.keys(),
                    "updated_at",
                ])
                for field, value in detail_defaults.items():
                    setattr(event, field, value)
                event.save(update_fields=list(detail_defaults))
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            "문화 동기화 완료: "
            f"신규 {created_count}, 갱신 {updated_count}, 장소 {Place.objects.count()}"
        ))

import json
from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from books.models import BookCategory, BookCategoryMap, BookDetail
from tastes.models import ContentItem


OUTPUT_DIR = settings.BASE_DIR.parent / "api_extract" / "book_data" / "output_kr"


def high_resolution_cover(url):
    if url and "image.aladin.co.kr" in url:
        return url.replace("/coversum/", "/cover500/")
    return url


def load_json(name):
    path = OUTPUT_DIR / name
    if not path.exists():
        raise CommandError(f"정제 파일이 없습니다: {path}")
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


class Command(BaseCommand):
    help = "정제된 도서 JSON을 DB에 생성 또는 갱신합니다."

    @transaction.atomic
    def handle(self, *args, **options):
        book_rows = load_json("book_details.json")
        category_rows = load_json("category_names.json")
        relation_rows = load_json("book_categories.json")

        category_by_aladin_id = {}
        for row in category_rows:
            category_id = row.get("aladin_category_id")
            if category_id is None:
                raise CommandError(f"카테고리 ID가 비어 있습니다: {row}")
            category, _ = BookCategory.objects.update_or_create(
                aladin_category_id=category_id,
                defaults={"name": row["name"]},
            )
            category_by_aladin_id[category.aladin_category_id] = category

        imported_item_ids = {row["aladin_item_id"] for row in book_rows}
        existing = {
            book.item_id: book
            for book in BookDetail.objects.select_related("content_item").all()
            if book.item_id in imported_item_ids
        }
        book_by_item_id = {}
        created_count = 0
        updated_count = 0

        for row in book_rows:
            item_id = row["aladin_item_id"]
            content_defaults = {
                "content_type": ContentItem.ContentType.BOOK,
                "title": row["title"],
                "summary": row["description"],
                "thumbnail_url": high_resolution_cover(row["cover"]),
                "source_url": row.get("link"),
                "is_adult": bool(row.get("adult", False)),
                "popularity_score": row.get("sales_point"),
            }
            detail_defaults = {
                "isbn10": row.get("isbn"),
                "isbn13": row.get("isbn13"),
                "author": row["author"],
                "publisher": row["publisher"],
                "pub_date": date.fromisoformat(row["pub_date"]),
                "price_sales": row.get("price_sales"),
                "price_standard": row.get("price_standard"),
                "mall_type": row.get("mall_type"),
                "stock_status": row.get("stock_status"),
                "mileage": row.get("mileage"),
                "sales_point": row.get("sales_point"),
                "customer_review_rank": row.get("customer_review_rank"),
                "fixed_price": row.get("fixed_price"),
                "series_info": row.get("series_info"),
                "has_ebook": bool(row.get("has_ebook", False)),
            }

            book = existing.get(item_id)
            if book is None:
                content_item = ContentItem.objects.create(**content_defaults)
                book = BookDetail.objects.create(
                    content_item=content_item,
                    item_id=item_id,
                    **detail_defaults,
                )
                created_count += 1
            else:
                for field, value in content_defaults.items():
                    setattr(book.content_item, field, value)
                book.content_item.save(update_fields=[
                    *content_defaults.keys(),
                    "updated_at",
                ])
                for field, value in detail_defaults.items():
                    setattr(book, field, value)
                book.save(update_fields=list(detail_defaults))
                updated_count += 1

            book_by_item_id[item_id] = book

        links = []
        seen_links = set()
        for row in relation_rows:
            key = (row["aladin_item_id"], row["aladin_category_id"])
            if key in seen_links:
                continue
            book = book_by_item_id.get(key[0])
            category = category_by_aladin_id.get(key[1])
            if book is None or category is None:
                raise CommandError(f"도서-카테고리 참조가 유효하지 않습니다: {row}")
            seen_links.add(key)
            links.append(BookCategoryMap(book_detail=book, category=category))
        relation_count_before = BookCategoryMap.objects.count()
        BookCategoryMap.objects.bulk_create(
            links,
            batch_size=2000,
            ignore_conflicts=True,
        )
        added_relation_count = BookCategoryMap.objects.count() - relation_count_before

        self.stdout.write(self.style.SUCCESS(
            "도서 동기화 완료: "
            f"신규 {created_count}, 갱신 {updated_count}, "
            f"카테고리 {len(category_by_aladin_id)}, 신규 관계 {added_relation_count}"
        ))

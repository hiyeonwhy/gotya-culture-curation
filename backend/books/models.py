from django.db import models

from tastes.models import ContentItem


class BookDetail(models.Model):
    content_item = models.OneToOneField(
        ContentItem,
        on_delete=models.CASCADE,
        related_name="book_detail",
    )
    item_id = models.PositiveBigIntegerField(unique=True)
    isbn10 = models.CharField(max_length=20, null=True, blank=True)
    isbn13 = models.CharField(max_length=20, null=True, blank=True)
    author = models.CharField(max_length=500)
    publisher = models.CharField(max_length=255)
    pub_date = models.DateField()
    price_sales = models.PositiveIntegerField(null=True, blank=True)
    price_standard = models.PositiveIntegerField(null=True, blank=True)
    mall_type = models.CharField(max_length=20, null=True, blank=True)
    stock_status = models.CharField(max_length=100, null=True, blank=True)
    mileage = models.PositiveIntegerField(null=True, blank=True)
    sales_point = models.PositiveIntegerField(null=True, blank=True)
    customer_review_rank = models.PositiveSmallIntegerField(null=True, blank=True)
    fixed_price = models.BooleanField(null=True, blank=True)
    series_info = models.JSONField(null=True, blank=True)
    has_ebook = models.BooleanField(default=False)

    class Meta:
        db_table = "book_details"
        ordering = ["-pub_date", "-sales_point"]

    def __str__(self):
        return self.content_item.title


class BookCategory(models.Model):
    # 기존 개발 DB에도 비대화식 migration이 가능하도록 null을 허용하되,
    # sync_books는 ID가 없는 정제 카테고리를 거부한다.
    aladin_category_id = models.PositiveIntegerField(
        unique=True,
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=500, unique=True)
    books = models.ManyToManyField(
        BookDetail,
        through="BookCategoryMap",
        related_name="categories",
        blank=True,
    )

    class Meta:
        db_table = "book_categories"
        ordering = ["name"]
        verbose_name_plural = "book categories"

    def __str__(self):
        return self.name


class BookCategoryMap(models.Model):
    book_detail = models.ForeignKey(
        BookDetail,
        on_delete=models.CASCADE,
        related_name="category_links",
    )
    category = models.ForeignKey(
        BookCategory,
        on_delete=models.CASCADE,
        related_name="book_links",
    )

    class Meta:
        db_table = "book_category_map"
        constraints = [
            models.UniqueConstraint(
                fields=["book_detail", "category"],
                name="unique_book_category",
            )
        ]

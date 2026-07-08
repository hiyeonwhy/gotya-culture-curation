from rest_framework import serializers

from books.models import BookCategory, BookDetail


class BookCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BookCategory
        fields = ("aladin_category_id", "name")


class BookListSerializer(serializers.ModelSerializer):
    content_id = serializers.IntegerField(source="content_item_id", read_only=True)
    title = serializers.CharField(source="content_item.title", read_only=True)
    thumbnail_url = serializers.SerializerMethodField()
    categories = BookCategorySerializer(many=True, read_only=True)

    def get_thumbnail_url(self, obj):
        url = obj.content_item.thumbnail_url
        if url and "image.aladin.co.kr" in url:
            return url.replace("/coversum/", "/cover500/")
        return url

    class Meta:
        model = BookDetail
        fields = (
            "content_id",
            "item_id",
            "title",
            "thumbnail_url",
            "author",
            "publisher",
            "pub_date",
            "sales_point",
            "customer_review_rank",
            "has_ebook",
            "categories",
        )


class BookDetailSerializer(BookListSerializer):
    summary = serializers.CharField(source="content_item.summary", read_only=True)
    source_url = serializers.URLField(source="content_item.source_url", read_only=True)
    is_adult = serializers.BooleanField(source="content_item.is_adult", read_only=True)
    popularity_score = serializers.FloatField(
        source="content_item.popularity_score",
        read_only=True,
    )

    class Meta(BookListSerializer.Meta):
        fields = BookListSerializer.Meta.fields + (
            "summary",
            "source_url",
            "is_adult",
            "popularity_score",
            "isbn10",
            "isbn13",
            "price_sales",
            "price_standard",
            "mall_type",
            "stock_status",
            "mileage",
            "fixed_price",
            "series_info",
        )

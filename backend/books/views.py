from django.db.models import Q
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny

from books.models import BookDetail
from books.pagination import BookPagination
from books.serializers import BookDetailSerializer, BookListSerializer


def parse_boolean(value, parameter_name):
    normalized = value.strip().lower()
    if normalized in {"true", "1"}:
        return True
    if normalized in {"false", "0"}:
        return False
    raise ValidationError({parameter_name: "true, false, 1, 0 중 하나여야 합니다."})


class BookListAPIView(ListAPIView):
    serializer_class = BookListSerializer
    permission_classes = (AllowAny,)
    pagination_class = BookPagination

    def get_queryset(self):
        queryset = BookDetail.objects.select_related("content_item").prefetch_related(
            "categories"
        )
        search = self.request.query_params.get("search", "").strip()
        search_scope = self.request.query_params.get("search_scope", "all").strip()
        category = self.request.query_params.get("category", "").strip()
        has_ebook = self.request.query_params.get("has_ebook")
        sort = self.request.query_params.get("sort", "popular")

        if search:
            search_filters = {
                "title": Q(content_item__title__icontains=search),
                "summary": Q(content_item__summary__icontains=search),
                "author": Q(author__icontains=search),
                "all": (
                    Q(content_item__title__icontains=search)
                    | Q(author__icontains=search)
                    | Q(publisher__icontains=search)
                    | Q(content_item__summary__icontains=search)
                ),
            }
            if search_scope not in search_filters:
                raise ValidationError({
                    "search_scope": "all, title, summary, author 중 하나여야 합니다."
                })
            queryset = queryset.filter(search_filters[search_scope])
        if category:
            if category.isdigit():
                queryset = queryset.filter(categories__aladin_category_id=int(category))
            else:
                queryset = queryset.filter(categories__name__icontains=category)
        if has_ebook is not None:
            queryset = queryset.filter(
                has_ebook=parse_boolean(has_ebook, "has_ebook")
            )

        ordering = {
            "popular": ("-sales_point", "-item_id"),
            "latest": ("-pub_date", "-item_id"),
            "rating": ("-customer_review_rank", "-sales_point", "-item_id"),
        }.get(sort, ("-sales_point", "-item_id"))
        return queryset.order_by(*ordering).distinct()


class BookDetailAPIView(RetrieveAPIView):
    serializer_class = BookDetailSerializer
    permission_classes = (AllowAny,)
    lookup_field = "item_id"
    lookup_url_kwarg = "item_id"
    queryset = BookDetail.objects.select_related("content_item").prefetch_related(
        "categories"
    )

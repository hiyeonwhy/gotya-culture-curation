from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from cultures.models import CultureEvent
from cultures.pagination import CulturePagination
from cultures.serializers import CultureDetailSerializer, CultureListSerializer


MAP_CATEGORIES = ("공연", "전시", "축제·행사")
AREA_ALIASES = {
    "강원": ("강원", "강원도", "강원특별자치도"),
    "전북": ("전북", "전라북도", "전북특별자치도"),
    "제주": ("제주", "제주도", "제주특별자치도"),
    "세종": ("세종", "세종시", "세종특별자치시"),
}


def normalize_area(area):
    for canonical, aliases in AREA_ALIASES.items():
        if area in aliases:
            return canonical
    return area


def area_filter(area):
    aliases = AREA_ALIASES.get(area, (area,))
    query = Q()
    for alias in aliases:
        query |= Q(place__area__iexact=alias)
    return query


def parse_boolean(value, parameter_name):
    normalized = value.strip().lower()
    if normalized in {"true", "1"}:
        return True
    if normalized in {"false", "0"}:
        return False
    raise ValidationError({parameter_name: "true, false, 1, 0 중 하나여야 합니다."})


class CultureRegionSummaryAPIView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        today = timezone.localdate()
        main_category = request.query_params.get("main_category", "").strip()
        if main_category and main_category not in MAP_CATEGORIES:
            raise ValidationError({"main_category": "지도에서 지원하지 않는 분류입니다."})

        regions = (
            CultureEvent.objects.filter(
                main_category__in=MAP_CATEGORIES,
                place__isnull=False,
                place__area__isnull=False,
                end_date__gte=today,
            )
            .exclude(place__area="")
        )
        if main_category:
            regions = regions.filter(main_category=main_category)

        regions = (
            regions.values("place__area")
            .annotate(count=Count("seq"))
            .order_by("place__area")
        )
        summary = {}
        for region in regions:
            area = normalize_area(region["place__area"])
            summary[area] = summary.get(area, 0) + region["count"]
        return Response(
            [{"area": area, "count": count} for area, count in summary.items()]
        )


class CultureListAPIView(ListAPIView):
    serializer_class = CultureListSerializer
    permission_classes = (AllowAny,)
    pagination_class = CulturePagination

    def get_queryset(self):
        today = timezone.localdate()
        queryset = CultureEvent.objects.select_related("content_item", "place").filter(
            end_date__gte=today,
        )
        params = self.request.query_params
        search = params.get("search", "").strip()
        search_scope = params.get("search_scope", "all").strip()
        main_category = params.get("main_category", "").strip()
        sub_category = params.get("sub_category", "").strip()
        area = params.get("area", "").strip()
        sigungu = params.get("sigungu", "").strip()
        ongoing = params.get("ongoing")
        map_only = params.get("map_only")
        map_scope = params.get("map_scope")
        sort = params.get("sort", "ending")

        if search:
            search_filters = {
                "title": Q(content_item__title__icontains=search),
                "summary": Q(content_item__summary__icontains=search),
                "place": Q(place__place_name__icontains=search) | Q(place__address__icontains=search),
                "all": (
                    Q(content_item__title__icontains=search)
                    | Q(content_item__summary__icontains=search)
                    | Q(place__place_name__icontains=search)
                    | Q(place__address__icontains=search)
                ),
            }
            if search_scope not in search_filters:
                raise ValidationError({
                    "search_scope": "all, title, summary, place 중 하나여야 합니다."
                })
            queryset = queryset.filter(search_filters[search_scope])
        if main_category:
            queryset = queryset.filter(main_category__iexact=main_category)
        if sub_category:
            queryset = queryset.filter(sub_category__iexact=sub_category)
        if area:
            queryset = queryset.filter(area_filter(area))
        if sigungu:
            queryset = queryset.filter(place__sigungu__iexact=sigungu)
        if ongoing is not None and parse_boolean(ongoing, "ongoing"):
            queryset = queryset.filter(start_date__lte=today, end_date__gte=today)
        if map_only is not None:
            map_available = parse_boolean(map_only, "map_only")
            queryset = queryset.filter(is_map_available=map_available)
            if map_available:
                queryset = queryset.filter(main_category__in=MAP_CATEGORIES)
        if map_scope is not None and parse_boolean(map_scope, "map_scope"):
            queryset = queryset.filter(
                main_category__in=MAP_CATEGORIES,
                place__isnull=False,
            )

        ordering = {
            "ending": ("end_date", "start_date", "seq"),
            "upcoming": ("start_date", "end_date", "seq"),
            "latest": ("-start_date", "-end_date", "seq"),
        }.get(sort, ("end_date", "start_date", "seq"))
        return queryset.order_by(*ordering)


class CultureDetailAPIView(RetrieveAPIView):
    serializer_class = CultureDetailSerializer
    permission_classes = (AllowAny,)
    lookup_field = "seq"
    lookup_url_kwarg = "seq"
    queryset = CultureEvent.objects.select_related("content_item", "place")

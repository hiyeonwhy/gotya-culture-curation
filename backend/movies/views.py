from django.db.models import Q
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny

from movies.models import MovieDetail
from movies.pagination import MoviePagination
from movies.serializers import MovieDetailSerializer, MovieListSerializer


class MovieListAPIView(ListAPIView):
    serializer_class = MovieListSerializer
    permission_classes = (AllowAny,)
    pagination_class = MoviePagination

    def get_queryset(self):
        queryset = MovieDetail.objects.select_related("content_item").prefetch_related(
            "genres"
        )
        search = self.request.query_params.get("search", "").strip()
        genre = self.request.query_params.get("genre", "").strip()
        sort = self.request.query_params.get("sort", "popular")

        if search:
            queryset = queryset.filter(
                Q(content_item__title__icontains=search)
                | Q(original_title__icontains=search)
                | Q(content_item__summary__icontains=search)
            )
        if genre:
            if genre.isdigit():
                queryset = queryset.filter(genres__tmdb_genre_id=int(genre))
            else:
                queryset = queryset.filter(genres__name__icontains=genre)

        ordering = {
            "popular": ("-popularity", "-vote_count", "-tmdb_id"),
            "latest": ("-release_date", "-tmdb_id"),
            "rating": ("-vote_average", "-vote_count", "-tmdb_id"),
        }.get(sort, ("-popularity", "-vote_count", "-tmdb_id"))
        return queryset.order_by(*ordering).distinct()


class MovieDetailAPIView(RetrieveAPIView):
    serializer_class = MovieDetailSerializer
    permission_classes = (AllowAny,)
    lookup_field = "tmdb_id"
    lookup_url_kwarg = "tmdb_id"
    queryset = MovieDetail.objects.select_related("content_item").prefetch_related(
        "genres"
    )

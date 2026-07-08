from rest_framework import serializers

from movies.models import GenreName, MovieDetail


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenreName
        fields = ("tmdb_genre_id", "name")


class MovieListSerializer(serializers.ModelSerializer):
    content_id = serializers.IntegerField(source="content_item_id", read_only=True)
    title = serializers.CharField(source="content_item.title", read_only=True)
    thumbnail_url = serializers.URLField(
        source="content_item.thumbnail_url",
        read_only=True,
    )
    genres = GenreSerializer(many=True, read_only=True)

    class Meta:
        model = MovieDetail
        fields = (
            "content_id",
            "tmdb_id",
            "title",
            "thumbnail_url",
            "release_date",
            "vote_average",
            "popularity",
            "genres",
        )


class MovieDetailSerializer(MovieListSerializer):
    summary = serializers.CharField(source="content_item.summary", read_only=True)
    source_url = serializers.URLField(source="content_item.source_url", read_only=True)
    is_adult = serializers.BooleanField(source="content_item.is_adult", read_only=True)
    popularity_score = serializers.FloatField(
        source="content_item.popularity_score",
        read_only=True,
    )

    class Meta(MovieListSerializer.Meta):
        fields = MovieListSerializer.Meta.fields + (
            "summary",
            "source_url",
            "is_adult",
            "popularity_score",
            "original_title",
            "original_language",
            "english_name",
            "poster_path",
            "backdrop_path",
            "vote_count",
            "softcore",
            "video",
        )

from django.db import models

from tastes.models import ContentItem


class MovieDetail(models.Model):
    content_item = models.OneToOneField(
        ContentItem,
        on_delete=models.CASCADE,
        related_name="movie_detail",
    )
    tmdb_id = models.PositiveBigIntegerField(unique=True)
    original_title = models.CharField(max_length=500)
    original_language = models.CharField(max_length=10)
    english_name = models.CharField(max_length=100, null=True, blank=True)
    poster_path = models.CharField(max_length=500)
    backdrop_path = models.CharField(max_length=500, null=True, blank=True)
    release_date = models.DateField()
    vote_average = models.FloatField()
    vote_count = models.PositiveIntegerField(null=True, blank=True)
    popularity = models.FloatField(null=True, blank=True)
    softcore = models.BooleanField(null=True, blank=True)
    video = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = "movie_details"
        ordering = ["-release_date", "-popularity"]
        indexes = [
            models.Index(fields=["release_date"], name="movie_release_idx"),
            models.Index(fields=["vote_average"], name="movie_vote_avg_idx"),
        ]

    def __str__(self):
        return self.content_item.title


class GenreName(models.Model):
    tmdb_genre_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=100, unique=True)
    movies = models.ManyToManyField(
        MovieDetail,
        through="MovieGenre",
        related_name="genres",
        blank=True,
    )

    class Meta:
        db_table = "genre_names"
        ordering = ["name"]

    def __str__(self):
        return self.name


class MovieGenre(models.Model):
    movie_detail = models.ForeignKey(
        MovieDetail,
        on_delete=models.CASCADE,
        related_name="genre_links",
    )
    genre_name = models.ForeignKey(
        GenreName,
        on_delete=models.CASCADE,
        related_name="movie_links",
    )

    class Meta:
        db_table = "movie_genres"
        constraints = [
            models.UniqueConstraint(
                fields=["movie_detail", "genre_name"],
                name="unique_movie_genre",
            )
        ]

import json
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from movies.models import GenreName, MovieDetail, MovieGenre
from tastes.models import ContentItem


OUTPUT_DIR = settings.BASE_DIR.parent / "api_extract" / "movie_data" / "output"


def load_json(name):
    path = OUTPUT_DIR / name
    if not path.exists():
        raise CommandError(f"정제 파일이 없습니다: {path}")
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def tmdb_image_url(path):
    if not path:
        return None
    if str(path).startswith(("http://", "https://")):
        return str(path)
    return f"https://image.tmdb.org/t/p/w500{path}"


class Command(BaseCommand):
    help = "정제된 영화 JSON을 DB에 생성 또는 갱신합니다."

    @transaction.atomic
    def handle(self, *args, **options):
        movie_rows = load_json("movie_details.json")
        genre_rows = load_json("genre_names.json")
        relation_rows = load_json("movie_genres.json")

        genre_by_tmdb_id = {}
        for row in genre_rows:
            genre, _ = GenreName.objects.update_or_create(
                tmdb_genre_id=row["tmdb_genre_id"],
                defaults={"name": row["name"]},
            )
            genre_by_tmdb_id[genre.tmdb_genre_id] = genre

        imported_tmdb_ids = {row["tmdb_id"] for row in movie_rows}
        existing = {
            movie.tmdb_id: movie
            for movie in MovieDetail.objects.select_related("content_item").all()
            if movie.tmdb_id in imported_tmdb_ids
        }
        movie_by_tmdb_id = {}
        created_count = 0
        updated_count = 0

        for row in movie_rows:
            tmdb_id = row["tmdb_id"]
            content_defaults = {
                "content_type": ContentItem.ContentType.MOVIE,
                "title": row["title"],
                "summary": row["overview"],
                "thumbnail_url": tmdb_image_url(row["poster_path"]),
                "source_url": f"https://www.themoviedb.org/movie/{tmdb_id}",
                "is_adult": bool(row.get("adult", False)),
                "popularity_score": row.get("popularity"),
            }
            detail_defaults = {
                "original_title": row["original_title"],
                "original_language": row["original_language"],
                "english_name": row.get("english_name"),
                "poster_path": row["poster_path"],
                "backdrop_path": row.get("backdrop_path"),
                "release_date": date.fromisoformat(row["release_date"]),
                "vote_average": row["vote_average"],
                "vote_count": row.get("vote_count"),
                "popularity": row.get("popularity"),
                "softcore": row.get("softcore"),
                "video": row.get("video"),
            }

            movie = existing.get(tmdb_id)
            if movie is None:
                content_item = ContentItem.objects.create(**content_defaults)
                movie = MovieDetail.objects.create(
                    content_item=content_item,
                    tmdb_id=tmdb_id,
                    **detail_defaults,
                )
                created_count += 1
            else:
                for field, value in content_defaults.items():
                    setattr(movie.content_item, field, value)
                movie.content_item.save(update_fields=[
                    *content_defaults.keys(),
                    "updated_at",
                ])
                for field, value in detail_defaults.items():
                    setattr(movie, field, value)
                movie.save(update_fields=list(detail_defaults))
                updated_count += 1

            movie_by_tmdb_id[tmdb_id] = movie

        links = []
        seen_links = set()
        for row in relation_rows:
            key = (row["tmdb_id"], row["tmdb_genre_id"])
            if key in seen_links:
                continue
            movie = movie_by_tmdb_id.get(key[0])
            genre = genre_by_tmdb_id.get(key[1])
            if movie is None or genre is None:
                raise CommandError(f"영화-장르 참조가 유효하지 않습니다: {row}")
            seen_links.add(key)
            links.append(MovieGenre(movie_detail=movie, genre_name=genre))
        relation_count_before = MovieGenre.objects.count()
        MovieGenre.objects.bulk_create(
            links,
            batch_size=2000,
            ignore_conflicts=True,
        )
        added_relation_count = MovieGenre.objects.count() - relation_count_before

        self.stdout.write(self.style.SUCCESS(
            "영화 동기화 완료: "
            f"신규 {created_count}, 갱신 {updated_count}, "
            f"장르 {len(genre_by_tmdb_id)}, 신규 관계 {added_relation_count}"
        ))

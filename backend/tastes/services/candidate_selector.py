from datetime import date

from books.models import BookDetail
from cultures.models import CultureEvent
from movies.models import MovieDetail

from .recommendation_mapping import TASTE_CONTENT_MAPPING


def _take_unique(primary, fallback, limit, excluded_content_ids):
    selected = []
    seen = set(excluded_content_ids)
    for row in [*primary, *fallback]:
        content_id = row.content_item_id
        if content_id in seen or row.content_item.is_adult:
            continue
        seen.add(content_id)
        selected.append(row)
        if len(selected) >= limit:
            break
    return selected


def _movie_candidate(movie):
    genres = [genre.name for genre in movie.genres.all()]
    return {
        "content_item_id": movie.content_item_id,
        "content_type": "movie",
        "title": movie.content_item.title,
        "summary": (movie.content_item.summary or "")[:500],
        "popularity_score": movie.content_item.popularity_score,
        "metadata": {
            "tmdb_id": movie.tmdb_id,
            "genres": genres,
            "release_date": movie.release_date.isoformat(),
            "vote_average": movie.vote_average,
        },
        "content_item": movie.content_item,
    }


def _book_candidate(book):
    categories = [category.name for category in book.categories.all()]
    return {
        "content_item_id": book.content_item_id,
        "content_type": "book",
        "title": book.content_item.title,
        "summary": (book.content_item.summary or "")[:500],
        "popularity_score": book.content_item.popularity_score,
        "metadata": {
            "aladin_item_id": book.item_id,
            "categories": categories,
            "author": book.author,
            "publisher": book.publisher,
            "pub_date": book.pub_date.isoformat(),
            "has_ebook": book.has_ebook,
        },
        "content_item": book.content_item,
    }


def _culture_candidate(event):
    return {
        "content_item_id": event.content_item_id,
        "content_type": "culture",
        "title": event.content_item.title,
        "summary": (event.content_item.summary or "")[:500],
        "popularity_score": event.content_item.popularity_score,
        "metadata": {
            "seq": event.seq,
            "main_category": event.main_category,
            "sub_category": event.sub_category,
            "start_date": event.start_date.isoformat(),
            "end_date": event.end_date.isoformat(),
            "place": event.place.place_name if event.place else None,
            "area": event.place.area if event.place else None,
        },
        "content_item": event.content_item,
    }


def select_candidates(profile, limit_per_type=30, exclude_content_ids=None):
    mapping = TASTE_CONTENT_MAPPING[profile["taste_type"]]
    excluded = set(profile["disliked_content_ids"])
    if exclude_content_ids:
        excluded.update(exclude_content_ids)
    fetch_limit = limit_per_type + len(excluded) + limit_per_type * 2
    use_random_order = profile.get("selection_source") == "random"
    use_taste_result_random_order = profile.get("selection_source") == "taste_result"

    movie_base = (
        MovieDetail.objects.select_related("content_item")
        .prefetch_related("genres")
        .filter(content_item__is_adult=False)
        .order_by("-popularity", "-vote_average", "-release_date")
    )
    if use_random_order:
        movie_primary = list(movie_base.order_by("?")[:fetch_limit])
    elif use_taste_result_random_order:
        movie_primary = list(
            movie_base.filter(
                genres__tmdb_genre_id__in=mapping["movie_genre_ids"]
            ).distinct().order_by("?")[:fetch_limit]
        )
    else:
        movie_primary = list(
            movie_base.filter(
                genres__tmdb_genre_id__in=mapping["movie_genre_ids"]
            ).distinct()[:fetch_limit]
        )
    movies = _take_unique(
        movie_primary,
        list(movie_base[:fetch_limit]),
        limit_per_type,
        excluded,
    )

    book_base = (
        BookDetail.objects.select_related("content_item")
        .prefetch_related("categories")
        .filter(content_item__is_adult=False)
        .order_by("-sales_point", "-customer_review_rank", "-pub_date")
    )
    if use_random_order:
        book_primary = list(book_base.order_by("?")[:fetch_limit])
    elif use_taste_result_random_order:
        book_primary = list(
            book_base.filter(
                categories__aladin_category_id__in=mapping["book_category_ids"]
            ).distinct().order_by("?")[:fetch_limit]
        )
    else:
        book_primary = list(
            book_base.filter(
                categories__aladin_category_id__in=mapping["book_category_ids"]
            ).distinct()[:fetch_limit]
        )
    books = _take_unique(
        book_primary,
        list(book_base[:fetch_limit]),
        limit_per_type,
        excluded,
    )

    culture_base = (
        CultureEvent.objects.select_related("content_item", "place")
        .filter(content_item__is_adult=False, end_date__gte=date.today())
        .order_by("start_date", "end_date", "content_item__title")
    )
    if use_random_order:
        culture_primary = list(culture_base.order_by("?")[:fetch_limit])
    elif use_taste_result_random_order:
        culture_primary = list(
            culture_base.filter(
                sub_category__in=mapping["culture_sub_categories"]
            ).order_by("?")[:fetch_limit]
        )
    else:
        culture_primary = list(
            culture_base.filter(
                sub_category__in=mapping["culture_sub_categories"]
            )[:fetch_limit]
        )
    cultures = _take_unique(
        culture_primary,
        list(culture_base[:fetch_limit]),
        limit_per_type,
        excluded,
    )

    return {
        "movie": [_movie_candidate(row) for row in movies],
        "book": [_book_candidate(row) for row in books],
        "culture": [_culture_candidate(row) for row in cultures],
    }

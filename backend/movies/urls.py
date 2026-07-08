from django.urls import path

from movies import views


app_name = "movies"

urlpatterns = [
    path("", views.MovieListAPIView.as_view(), name="movie-list"),
    path("<int:tmdb_id>/", views.MovieDetailAPIView.as_view(), name="movie-detail"),
]

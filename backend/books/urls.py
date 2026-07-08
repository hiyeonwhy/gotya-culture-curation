from django.urls import path

from books import views


app_name = "books"

urlpatterns = [
    path("", views.BookListAPIView.as_view(), name="book-list"),
    path("<int:item_id>/", views.BookDetailAPIView.as_view(), name="book-detail"),
]

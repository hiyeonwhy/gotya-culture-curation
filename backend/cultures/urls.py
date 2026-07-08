from django.urls import path

from cultures import views


app_name = "cultures"

urlpatterns = [
    path("regions/summary/", views.CultureRegionSummaryAPIView.as_view(), name="culture-region-summary"),
    path("", views.CultureListAPIView.as_view(), name="culture-list"),
    path("<str:seq>/", views.CultureDetailAPIView.as_view(), name="culture-detail"),
]

from django.db import models

from tastes.models import ContentItem


class Place(models.Model):
    place_name = models.CharField(max_length=500, null=True, blank=True)
    area = models.CharField(max_length=100, null=True, blank=True)
    sigungu = models.CharField(max_length=100, null=True, blank=True)
    address = models.CharField(max_length=1000, null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = "places"
        constraints = [
            models.UniqueConstraint(
                fields=["place_name", "address"],
                name="unique_place_name_address",
            )
        ]
        indexes = [
            models.Index(fields=["area", "sigungu"], name="place_region_idx"),
        ]
        ordering = ["area", "sigungu", "place_name"]

    def __str__(self):
        return self.place_name or self.address or f"장소 {self.pk}"


class CultureEvent(models.Model):
    content_item = models.OneToOneField(
        ContentItem,
        on_delete=models.CASCADE,
        related_name="culture_event",
    )
    place = models.ForeignKey(
        Place,
        on_delete=models.SET_NULL,
        related_name="culture_events",
        null=True,
        blank=True,
    )
    seq = models.CharField(max_length=100, unique=True)
    main_category = models.CharField(max_length=100)
    sub_category = models.CharField(max_length=100)
    realm_code = models.CharField(max_length=50, null=True, blank=True)
    realm_name = models.CharField(max_length=100, null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    price = models.TextField(null=True, blank=True)
    contact = models.CharField(max_length=500, null=True, blank=True)
    is_map_available = models.BooleanField(default=False)

    class Meta:
        db_table = "culture_events"
        ordering = ["end_date", "start_date"]
        indexes = [
            models.Index(fields=["main_category"], name="culture_main_cat_idx"),
            models.Index(fields=["sub_category"], name="culture_sub_cat_idx"),
            models.Index(fields=["start_date", "end_date"], name="culture_period_idx"),
        ]

    def __str__(self):
        return self.content_item.title

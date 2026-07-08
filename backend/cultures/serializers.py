from rest_framework import serializers

from cultures.models import CultureEvent, Place


class PlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Place
        fields = (
            "place_name",
            "area",
            "sigungu",
            "address",
            "longitude",
            "latitude",
        )


class CultureListSerializer(serializers.ModelSerializer):
    content_id = serializers.IntegerField(source="content_item_id", read_only=True)
    title = serializers.CharField(source="content_item.title", read_only=True)
    thumbnail_url = serializers.URLField(
        source="content_item.thumbnail_url",
        read_only=True,
    )
    place = PlaceSerializer(read_only=True)

    class Meta:
        model = CultureEvent
        fields = (
            "content_id",
            "seq",
            "title",
            "thumbnail_url",
            "main_category",
            "sub_category",
            "start_date",
            "end_date",
            "is_map_available",
            "place",
        )


class CultureDetailSerializer(CultureListSerializer):
    source_url = serializers.URLField(source="content_item.source_url", read_only=True)

    class Meta(CultureListSerializer.Meta):
        fields = CultureListSerializer.Meta.fields + (
            "source_url",
            "realm_code",
            "realm_name",
            "price",
            "contact",
        )

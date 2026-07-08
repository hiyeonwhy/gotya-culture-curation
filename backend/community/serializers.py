from rest_framework import serializers

from .models import Comment, Post


class AuthorSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    nickname = serializers.CharField(read_only=True)
    profile_image = serializers.URLField(read_only=True, allow_null=True)


class CommentSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(source="user", read_only=True)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = (
            "id",
            "post",
            "author",
            "content",
            "is_owner",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "post", "author", "is_owner", "created_at", "updated_at")

    def validate_content(self, value):
        content = value.strip()
        if not content:
            raise serializers.ValidationError("댓글 내용을 입력해 주세요.")
        return content

    def get_is_owner(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.user_id == request.user.id)


class PostListSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(source="user", read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    comment_count = serializers.IntegerField(read_only=True)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id",
            "category",
            "category_display",
            "title",
            "author",
            "view_count",
            "comment_count",
            "is_owner",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_is_owner(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.user_id == request.user.id)


class PostDetailSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(source="user", read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    comment_count = serializers.IntegerField(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id",
            "category",
            "category_display",
            "title",
            "content",
            "author",
            "view_count",
            "comment_count",
            "comments",
            "is_owner",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "category_display",
            "author",
            "view_count",
            "comment_count",
            "comments",
            "is_owner",
            "created_at",
            "updated_at",
        )

    def validate_title(self, value):
        title = value.strip()
        if not title:
            raise serializers.ValidationError("제목을 입력해 주세요.")
        return title

    def validate_content(self, value):
        content = value.strip()
        if not content:
            raise serializers.ValidationError("내용을 입력해 주세요.")
        return content

    def get_is_owner(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.user_id == request.user.id)

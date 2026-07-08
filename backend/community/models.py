from django.conf import settings
from django.db import models


class Post(models.Model):
    class Category(models.TextChoices):
        RECOMMENDATION = "recommendation", "추천"
        REVIEW = "review", "후기"
        QUESTION = "question", "질문"
        FREE = "free", "자유"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    title = models.CharField(max_length=255)
    content = models.TextField()
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "posts"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["category"], name="post_category_idx")]

    def __str__(self):
        return self.title


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "comments"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user} - {self.post}"

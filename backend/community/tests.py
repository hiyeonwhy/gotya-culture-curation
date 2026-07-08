from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import Comment, Post


User = get_user_model()


class CommunityApiTests(APITestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            login_id="author",
            password="StrongPass123!",
            nickname="작성자",
        )
        self.other = User.objects.create_user(
            login_id="other",
            password="StrongPass123!",
            nickname="다른사람",
        )
        self.author_token = Token.objects.create(user=self.author)
        self.other_token = Token.objects.create(user=self.other)
        self.post = Post.objects.create(
            user=self.author,
            category=Post.Category.REVIEW,
            title="첫 번째 후기",
            content="좋았던 콘텐츠 후기입니다.",
        )

    def authenticate(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_anyone_can_list_and_filter_posts(self):
        Post.objects.create(
            user=self.author,
            category=Post.Category.QUESTION,
            title="질문 글",
            content="질문입니다.",
        )

        response = self.client.get("/api/community/posts/?category=review")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["category"], "review")

    def test_authenticated_user_can_create_post(self):
        self.authenticate(self.other_token)

        response = self.client.post(
            "/api/community/posts/",
            {"category": "question", "title": "궁금해요", "content": "내용입니다."},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["author"]["id"], self.other.id)
        self.assertTrue(Post.objects.filter(user=self.other, title="궁금해요").exists())

    def test_anonymous_user_cannot_create_post(self):
        response = self.client.post(
            "/api/community/posts/",
            {"category": "question", "title": "익명 글", "content": "내용"},
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_only_owner_can_update_or_delete_post(self):
        self.authenticate(self.other_token)

        response = self.client.patch(
            f"/api/community/posts/{self.post.id}/",
            {"title": "수정 시도"},
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, "첫 번째 후기")

    def test_retrieve_increases_view_count(self):
        response = self.client.get(f"/api/community/posts/{self.post.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["view_count"], 1)

    def test_retrieve_can_skip_view_count_for_edit_form(self):
        response = self.client.get(
            f"/api/community/posts/{self.post.id}/?track_view=false"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["view_count"], 0)

    def test_authenticated_user_can_create_comment(self):
        self.authenticate(self.other_token)

        response = self.client.post(
            f"/api/community/posts/{self.post.id}/comments/",
            {"content": "좋은 후기네요."},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["author"]["id"], self.other.id)
        self.assertTrue(Comment.objects.filter(post=self.post, user=self.other).exists())

    def test_only_owner_can_delete_comment(self):
        comment = Comment.objects.create(post=self.post, user=self.author, content="작성자 댓글")
        self.authenticate(self.other_token)

        response = self.client.delete(f"/api/community/comments/{comment.id}/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Comment.objects.filter(pk=comment.pk).exists())

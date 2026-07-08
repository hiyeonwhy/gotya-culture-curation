from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase


User = get_user_model()


class AuthenticationAPITests(APITestCase):
    password = "A9!vL2@qZ7#n"

    def signup_payload(self, **overrides):
        payload = {
            "login_id": "member01",
            "nickname": "오늘뭐함회원",
            "password": self.password,
            "password_confirm": self.password,
        }
        payload.update(overrides)
        return payload

    def create_user(self):
        return User.objects.create_user(
            login_id="member01",
            nickname="오늘뭐함회원",
            password=self.password,
        )

    def test_signup_creates_hashed_user_and_returns_token(self):
        response = self.client.post(
            reverse("accounts:signup"),
            self.signup_payload(),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(login_id="member01")
        self.assertTrue(user.check_password(self.password))
        self.assertNotEqual(user.password, self.password)
        self.assertEqual(response.data["user"]["nickname"], "오늘뭐함회원")
        self.assertTrue(Token.objects.filter(key=response.data["token"], user=user).exists())
        self.assertNotIn("password", response.data["user"])

    def test_signup_rejects_case_insensitive_duplicate_login_id(self):
        self.create_user()
        response = self.client.post(
            reverse("accounts:signup"),
            self.signup_payload(
                login_id="MEMBER01",
                nickname="다른닉네임",
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("login_id", response.data)

    def test_signup_rejects_password_mismatch(self):
        response = self.client.post(
            reverse("accounts:signup"),
            self.signup_payload(password_confirm="Different9!Password"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_confirm", response.data)

    def test_login_returns_token_and_user(self):
        user = self.create_user()
        response = self.client.post(
            reverse("accounts:login"),
            {"login_id": "MEMBER01", "password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["id"], user.id)
        self.assertTrue(Token.objects.filter(key=response.data["token"], user=user).exists())

    def test_login_rejects_invalid_credentials(self):
        self.create_user()
        response = self.client.post(
            reverse("accounts:login"),
            {"login_id": "member01", "password": "wrong-password"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_me_returns_authenticated_user(self):
        user = self.create_user()
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.get(reverse("accounts:me"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["login_id"], user.login_id)

    def test_authenticated_user_can_update_profile(self):
        user = self.create_user()
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.patch(
            reverse("accounts:me"),
            {
                "login_id": "updated-member",
                "nickname": "수정된회원",
                "email": "member@example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["login_id"], "updated-member")
        self.assertEqual(response.data["nickname"], "수정된회원")
        self.assertEqual(response.data["email"], "member@example.com")
        user.refresh_from_db()
        self.assertEqual(user.login_id, "updated-member")

    def test_authenticated_user_can_update_password(self):
        user = self.create_user()
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        new_password = "NewStrongPass123!"

        response = self.client.patch(
            reverse("accounts:me"),
            {
                "login_id": user.login_id,
                "nickname": user.nickname,
                "email": "member@example.com",
                "password": new_password,
                "password_confirm": new_password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.check_password(new_password))

    def test_profile_update_rejects_password_mismatch(self):
        user = self.create_user()
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.patch(
            reverse("accounts:me"),
            {
                "login_id": user.login_id,
                "nickname": user.nickname,
                "password": "NewStrongPass123!",
                "password_confirm": "DifferentPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_confirm", response.data)

    def test_profile_update_rejects_duplicate_login_id(self):
        user = self.create_user()
        User.objects.create_user(
            login_id="already-used",
            nickname="이미있는회원",
            password=self.password,
        )
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.patch(
            reverse("accounts:me"),
            {
                "login_id": "already-used",
                "nickname": user.nickname,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("login_id", response.data)

    def test_superuser_only_requires_login_id_and_password(self):
        user = User.objects.create_superuser(login_id="admin", password=self.password)

        self.assertEqual(user.login_id, "admin")
        self.assertEqual(user.nickname, "admin")
        self.assertIsNone(user.email)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_logout_deletes_token(self):
        user = self.create_user()
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.post(reverse("accounts:logout"))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Token.objects.filter(key=token.key).exists())

        me_response = self.client.get(reverse("accounts:me"))
        self.assertEqual(me_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_upload_profile_image(self):
        user = self.create_user()
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        image = SimpleUploadedFile(
            "profile.gif",
            b"GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00"
            b"\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
            content_type="image/gif",
        )

        response = self.client.patch(
            reverse("accounts:profile-image-upload"),
            {"profile_image": image},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("/media/profiles/", response.data["profile_image"])
        user.refresh_from_db()
        self.assertEqual(user.profile_image, response.data["profile_image"])

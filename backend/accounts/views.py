from django.contrib.auth.models import update_last_login
from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction
from pathlib import Path
from uuid import uuid4

from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    LoginSerializer,
    ProfileImageUploadSerializer,
    ProfileUpdateSerializer,
    SignupSerializer,
    UserSerializer,
)


def authentication_response(user, token):
    return {
        "token": token.key,
        "user": UserSerializer(user).data,
    }


class SignupView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token = Token.objects.create(user=user)
        return Response(
            authentication_response(user, token),
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        update_last_login(None, user)
        return Response(authentication_response(user, token), status=status.HTTP_200_OK)


class LogoutView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)


class ProfileImageUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request):
        serializer = ProfileImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        image = serializer.validated_data["profile_image"]
        extension = Path(image.name).suffix.lower() or ".jpg"
        file_path = f"profiles/{request.user.id}_{uuid4().hex}{extension}"
        saved_path = default_storage.save(file_path, image)
        image_url = request.build_absolute_uri(f"{settings.MEDIA_URL}{saved_path}")

        request.user.profile_image = image_url
        request.user.save(update_fields=["profile_image", "updated_at"])

        return Response(
            UserSerializer(request.user).data,
            status=status.HTTP_200_OK,
        )

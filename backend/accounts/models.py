from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, login_id, password, **extra_fields):
        if not login_id:
            raise ValueError("아이디는 필수입니다.")
        login_id = login_id.strip().lower()
        extra_fields.setdefault("nickname", login_id)
        user = self.model(login_id=login_id, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, login_id, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(login_id, password, **extra_fields)

    def create_superuser(self, login_id, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("슈퍼유저는 is_staff=True여야 합니다.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("슈퍼유저는 is_superuser=True여야 합니다.")
        return self._create_user(login_id, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    login_id = models.CharField("아이디", max_length=50, unique=True)
    email = models.EmailField(null=True, blank=True)
    nickname = models.CharField(max_length=50, unique=True)
    profile_image = models.URLField(max_length=500, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "login_id"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]

    def __str__(self):
        return self.nickname

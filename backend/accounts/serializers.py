from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "login_id",
            "nickname",
            "email",
            "profile_image",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = ("login_id", "nickname", "password", "password_confirm")

    def validate_login_id(self, value):
        login_id = value.strip().lower()
        if not login_id:
            raise serializers.ValidationError("아이디를 입력해 주세요.")
        if User.objects.filter(login_id=login_id).exists():
            raise serializers.ValidationError("이미 사용 중인 아이디입니다.")
        return login_id

    def validate_nickname(self, value):
        nickname = value.strip()
        if not nickname:
            raise serializers.ValidationError("닉네임을 입력해 주세요.")
        if User.objects.filter(nickname=nickname).exists():
            raise serializers.ValidationError("이미 사용 중인 닉네임입니다.")
        return nickname

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "비밀번호가 일치하지 않습니다."}
            )

        candidate = User(login_id=attrs["login_id"], nickname=attrs["nickname"])
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                {"password": list(error.messages)}
            ) from error
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)


class LoginSerializer(serializers.Serializer):
    login_id = serializers.CharField(max_length=50)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        login_id = attrs["login_id"].strip().lower()
        existing_user = User.objects.filter(login_id=login_id).first()

        if existing_user is not None and not existing_user.is_active:
            raise serializers.ValidationError("비활성화된 계정입니다.")

        user = authenticate(
            request=self.context.get("request"),
            login_id=login_id,
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError("아이디 또는 비밀번호가 올바르지 않습니다.")

        attrs["user"] = user
        return attrs


class ProfileUpdateSerializer(serializers.ModelSerializer):
    login_id = serializers.CharField(max_length=50)
    nickname = serializers.CharField(max_length=50)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    password = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
        trim_whitespace=False,
    )
    password_confirm = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
        trim_whitespace=False,
    )

    class Meta:
        model = User
        fields = ("login_id", "nickname", "email", "password", "password_confirm")

    def validate_login_id(self, value):
        login_id = value.strip().lower()
        if not login_id:
            raise serializers.ValidationError("아이디를 입력해 주세요.")
        queryset = User.objects.filter(login_id=login_id)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("이미 사용 중인 아이디입니다.")
        return login_id

    def validate_nickname(self, value):
        nickname = value.strip()
        if not nickname:
            raise serializers.ValidationError("닉네임을 입력해 주세요.")
        queryset = User.objects.filter(nickname=nickname)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("이미 사용 중인 닉네임입니다.")
        return nickname

    def validate(self, attrs):
        if attrs.get("email") == "":
            attrs["email"] = None

        password = attrs.get("password", "")
        password_confirm = attrs.get("password_confirm", "")
        if password or password_confirm:
            if password != password_confirm:
                raise serializers.ValidationError(
                    {"password_confirm": "비밀번호가 일치하지 않습니다."}
                )
            try:
                validate_password(password, user=self.instance)
            except DjangoValidationError as error:
                raise serializers.ValidationError(
                    {"password": list(error.messages)}
                ) from error
        return attrs

    def update(self, instance, validated_data):
        password = validated_data.pop("password", "")
        validated_data.pop("password_confirm", None)

        for field, value in validated_data.items():
            setattr(instance, field, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance


class ProfileImageUploadSerializer(serializers.Serializer):
    profile_image = serializers.FileField()

    def validate_profile_image(self, value):
        content_type = getattr(value, "content_type", "")
        if not content_type.startswith("image/"):
            raise serializers.ValidationError("이미지 파일만 업로드할 수 있습니다.")
        max_size = 5 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("프로필 이미지는 5MB 이하로 업로드해 주세요.")
        return value

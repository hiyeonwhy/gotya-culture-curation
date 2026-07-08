from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth.password_validation import validate_password


User = get_user_model()


class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="비밀번호", widget=forms.PasswordInput)
    password2 = forms.CharField(label="비밀번호 확인", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("login_id", "nickname", "profile_image")

    def clean_login_id(self):
        login_id = self.cleaned_data["login_id"].strip().lower()
        if User.objects.filter(login_id=login_id).exists():
            raise forms.ValidationError("이미 사용 중인 아이디입니다.")
        return login_id

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("비밀번호가 일치하지 않습니다.")
        if password2:
            validate_password(password2, self.instance)
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(label="비밀번호")

    class Meta:
        model = User
        fields = (
            "login_id",
            "nickname",
            "profile_image",
            "password",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )

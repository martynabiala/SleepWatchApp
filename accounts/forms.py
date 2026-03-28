from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)

from .models import UserProfile


User = get_user_model()


class SignupForm(UserCreationForm):
    email = forms.EmailField(label="Adres e-mail", max_length=254)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Konto z takim adresem e-mail juz istnieje.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower()
        user.is_active = False
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Login")
    password = forms.CharField(label="Haslo", widget=forms.PasswordInput)


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(label="Adres e-mail", max_length=254)

    class Meta:
        model = User
        fields = ("username", "email")
        labels = {
            "username": "Login",
        }

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        qs = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ten adres e-mail jest juz zajety.")
        return email


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = (
            "display_name",
            "age_group",
            "lifestyle",
            "sleep_goal_hours",
        )
        labels = {
            "sleep_goal_hours": "Docelowy czas snu",
        }


class SleepWatchPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(label="Adres e-mail", max_length=254)


class SleepWatchSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label="Nowe haslo",
        widget=forms.PasswordInput,
    )
    new_password2 = forms.CharField(
        label="Powtorz nowe haslo",
        widget=forms.PasswordInput,
    )

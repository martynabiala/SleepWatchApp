import base64

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.core.validators import FileExtensionValidator

from .models import BugReport, UserProfile


User = get_user_model()


def build_unique_username_from_email(email):
    base_username = email.split("@", 1)[0].strip() or "u\u017cytkownik"
    username = base_username[:150]
    counter = 2

    while User.objects.filter(username__iexact=username).exists():
        suffix = str(counter)
        username = f"{base_username[:150 - len(suffix) - 1]}_{suffix}"
        counter += 1

    return username


class SignupForm(UserCreationForm):
    email = forms.EmailField(label="Adres e-mail", max_length=254)
    age_group = forms.ChoiceField(
        label="Grupa wiekowa",
        choices=[("", "Wybierz")] + UserProfile.AGE_GROUP_CHOICES,
    )
    parent_email = forms.EmailField(
        label="Adres e-mail rodzica lub opiekuna",
        max_length=254,
        required=False,
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email", "age_group", "parent_email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "username" in self.fields:
            self.fields.pop("username")
        for field_name in ("password1", "password2"):
            if field_name in self.fields:
                self.fields[field_name].help_text = ""
        self.fields["email"].help_text = ""
        self.fields["age_group"].help_text = ""
        self.fields["parent_email"].help_text = ""

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Konto z takim adresem e-mail ju\u017c istnieje.")
        return email

    def clean_parent_email(self):
        return self.cleaned_data.get("parent_email", "").lower()

    def clean(self):
        cleaned_data = super().clean()
        age_group = cleaned_data.get("age_group")
        email = cleaned_data.get("email")
        parent_email = cleaned_data.get("parent_email")

        if age_group == UserProfile.AGE_GROUP_UNDER_18:
            if not parent_email:
                self.add_error("parent_email", "Dla konta dziecka podaj adres e-mail rodzica lub opiekuna.")
            elif parent_email == email:
                self.add_error("parent_email", "Adres rodzica lub opiekuna musi by\u0107 inny ni\u017c adres dziecka.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower()
        user.username = build_unique_username_from_email(user.email)
        user.is_active = False
        if commit:
            user.save()
            profile = user.profile
            profile.display_name = user.email.split("@", 1)[0]
            profile.age_group = self.cleaned_data["age_group"]
            profile.is_child_account = self.cleaned_data["age_group"] == UserProfile.AGE_GROUP_UNDER_18
            profile.parent_email = self.cleaned_data["parent_email"]
            profile.parental_consent_granted = not profile.is_child_account
            profile.parental_consent_at = None
            profile.save(
                update_fields=[
                    "display_name",
                    "age_group",
                    "is_child_account",
                    "parent_email",
                    "parental_consent_granted",
                    "parental_consent_at",
                ]
            )
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Login lub adres e-mail")
    password = forms.CharField(label="Has\u0142o", widget=forms.PasswordInput)

    def clean(self):
        username = self.cleaned_data.get("username")
        if username and "@" in username:
            try:
                user = User.objects.get(email__iexact=username)
            except User.DoesNotExist:
                pass
            else:
                self.cleaned_data["username"] = user.username
        return super().clean()


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("username",)
        labels = {
            "username": "Login",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = ""

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        qs = User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ten login jest ju\u017c zaj\u0119ty.")
        return username


class ProfileForm(forms.ModelForm):
    avatar_image = forms.ImageField(
        label="Zdjecie z urzadzenia",
        required=False,
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "gif", "webp"])],
        widget=forms.FileInput(attrs={"accept": "image/*"}),
    )

    class Meta:
        model = UserProfile
        fields = (
            "display_name",
            "avatar",
            "avatar_image",
            "age_group",
            "lifestyle",
            "sleep_goal_hours",
        )
        labels = {
            "sleep_goal_hours": "Docelowy czas snu",
        }
        widgets = {
            "avatar": forms.RadioSelect,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["avatar"].help_text = ""
        self.fields["avatar_image"].help_text = "JPG, PNG, GIF lub WebP, maksymalnie 5 MB."

    def clean_avatar_image(self):
        avatar_image = self.cleaned_data.get("avatar_image")
        if avatar_image and avatar_image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Zdjecie awatara moze miec maksymalnie 5 MB.")
        return avatar_image

    def save(self, commit=True):
        profile = super().save(commit=False)
        avatar_image = self.cleaned_data.get("avatar_image")
        if avatar_image:
            profile.avatar_image_data = base64.b64encode(avatar_image.read()).decode("ascii")
            profile.avatar_image_mime = avatar_image.content_type or "image/jpeg"
            avatar_image.seek(0)

        if commit:
            profile.save()
            self.save_m2m()
        return profile


class SleepWatchPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(label="Adres e-mail", max_length=254)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].help_text = ""


class SleepWatchSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label="Nowe has\u0142o",
        widget=forms.PasswordInput,
    )
    new_password2 = forms.CharField(
        label="Powt\u00f3rz nowe has\u0142o",
        widget=forms.PasswordInput,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].help_text = ""
        self.fields["new_password2"].help_text = ""


class SyncSourceSelectionForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ("preferred_sync_source",)
        labels = {
            "preferred_sync_source": "Preferowane \u017ar\u00f3d\u0142o danych",
        }
        widgets = {
            "preferred_sync_source": forms.RadioSelect,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["preferred_sync_source"].choices = [
            (UserProfile.SYNC_SOURCE_MANUAL_CSV, "Import pliku CSV"),
        ]
        self.fields["preferred_sync_source"].help_text = ""


class MonthlyHypothesisForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ("active_hypothesis",)
        labels = {
            "active_hypothesis": "Czynnik",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["active_hypothesis"].help_text = ""


class BugReportForm(forms.ModelForm):
    class Meta:
        model = BugReport
        fields = (
            "category",
            "description",
        )
        labels = {
            "category": "Rodzaj zgłoszenia",
            "description": "Opis problemu",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 8}),
        }
        help_texts = {
            "description": "Napisz, co widzisz i co utrudnia korzystanie z aplikacji.",
        }

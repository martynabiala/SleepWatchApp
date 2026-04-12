from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    SYNC_SOURCE_HEALTH_CONNECT = "health_connect"
    SYNC_SOURCE_ZEPP_LIFE = "zepp_life"

    AGE_GROUP_UNDER_18 = "under_18"
    AGE_GROUP_18_25 = "18-25"
    AGE_GROUP_26_35 = "26-35"
    AGE_GROUP_36_50 = "36-50"
    AGE_GROUP_51_PLUS = "51+"

    ACTIVITY_SEDENTARY = "sedentary"
    ACTIVITY_MODERATE = "moderate"
    ACTIVITY_PHYSICAL_HIGH = "physical_high"

    AVATAR_MOON = "moon"
    AVATAR_STAR = "star"
    AVATAR_CLOUD = "cloud"
    AVATAR_SUN = "sun"
    AVATAR_LEAF = "leaf"
    AVATAR_HEART = "heart"

    PREFERRED_SYNC_SOURCE_CHOICES = [
        (SYNC_SOURCE_HEALTH_CONNECT, "Health Connect"),
        (SYNC_SOURCE_ZEPP_LIFE, "Zepp Life"),
    ]

    AGE_GROUP_CHOICES = [
        (AGE_GROUP_UNDER_18, "Poniżej 18 lat"),
        (AGE_GROUP_18_25, "18-25 lat"),
        (AGE_GROUP_26_35, "26-35 lat"),
        (AGE_GROUP_36_50, "36-50 lat"),
        (AGE_GROUP_51_PLUS, "51+ lat"),
    ]

    LIFESTYLE_CHOICES = [
        (ACTIVITY_SEDENTARY, "Tryb siedzący, znikoma aktywność"),
        (ACTIVITY_MODERATE, "Umiarkowana aktywność fizyczna"),
        (ACTIVITY_PHYSICAL_HIGH, "Praca fizyczna, duża aktywność"),
    ]

    AVATAR_CHOICES = [
        (AVATAR_MOON, "Księżyc"),
        (AVATAR_STAR, "Gwiazda"),
        (AVATAR_CLOUD, "Chmurka"),
        (AVATAR_SUN, "Słońce"),
        (AVATAR_LEAF, "Listek"),
        (AVATAR_HEART, "Serce"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    display_name = models.CharField("Nazwa użytkownika", max_length=100, blank=True)
    avatar = models.CharField(
        "Awatar",
        max_length=20,
        choices=AVATAR_CHOICES,
        default=AVATAR_MOON,
    )
    age_group = models.CharField(
        "Grupa wiekowa",
        max_length=10,
        choices=AGE_GROUP_CHOICES,
        blank=True,
    )
    is_child_account = models.BooleanField("Czy konto dziecka", default=False)
    parent_email = models.EmailField("E-mail rodzica", blank=True)
    parental_consent_granted = models.BooleanField("Zgoda rodzica", default=False)
    parental_consent_at = models.DateTimeField("Data zgody rodzica", null=True, blank=True)
    lifestyle = models.CharField(
        "Aktywność fizyczna",
        max_length=20,
        choices=LIFESTYLE_CHOICES,
        blank=True,
    )
    sleep_goal_hours = models.PositiveSmallIntegerField(
        "Docelowa długość snu",
        default=8,
    )
    preferred_sync_source = models.CharField(
        "Preferowane zrodlo synchronizacji",
        max_length=20,
        choices=PREFERRED_SYNC_SOURCE_CHOICES,
        default=SYNC_SOURCE_HEALTH_CONNECT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil użytkownika"
        verbose_name_plural = "Profile użytkowników"

    def __str__(self):
        return self.display_name or f"Profil {self.user.username}"

    @property
    def avatar_symbol(self):
        return {
            self.AVATAR_MOON: "☾",
            self.AVATAR_STAR: "★",
            self.AVATAR_CLOUD: "☁",
            self.AVATAR_SUN: "☀",
            self.AVATAR_LEAF: "❋",
            self.AVATAR_HEART: "♥",
        }.get(self.avatar, "☾")

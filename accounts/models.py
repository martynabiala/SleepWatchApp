from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    AGE_GROUP_18_25 = "18-25"
    AGE_GROUP_26_35 = "26-35"
    AGE_GROUP_36_50 = "36-50"
    AGE_GROUP_51_PLUS = "51+"

    ACTIVITY_SEDENTARY = "sedentary"
    ACTIVITY_MODERATE = "moderate"
    ACTIVITY_PHYSICAL_HIGH = "physical_high"

    AGE_GROUP_CHOICES = [
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

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    display_name = models.CharField("Nazwa użytkownika", max_length=100, blank=True)
    age_group = models.CharField(
        "Grupa wiekowa",
        max_length=10,
        choices=AGE_GROUP_CHOICES,
        blank=True,
    )
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil użytkownika"
        verbose_name_plural = "Profile użytkowników"

    def __str__(self):
        return self.display_name or f"Profil {self.user.username}"

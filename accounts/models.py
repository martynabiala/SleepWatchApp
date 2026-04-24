from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    SYNC_SOURCE_HEALTH_CONNECT = "health_connect"
    SYNC_SOURCE_MANUAL_CSV = "manual_csv"
    HYPOTHESIS_NONE = ""
    HYPOTHESIS_CAFFEINE = "caffeine"
    HYPOTHESIS_STRESS = "stress"
    HYPOTHESIS_NAP = "nap"
    HYPOTHESIS_ALCOHOL = "alcohol"
    HYPOTHESIS_TRAINING = "training"

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
        (SYNC_SOURCE_HEALTH_CONNECT, "Synchronizacja z telefonu"),
        (SYNC_SOURCE_MANUAL_CSV, "Import pliku CSV"),
    ]

    HYPOTHESIS_CHOICES = [
        (HYPOTHESIS_NONE, "Bez aktywnej hipotezy"),
        (HYPOTHESIS_CAFFEINE, "Sprawdzam wpływ kofeiny na sen"),
        (HYPOTHESIS_STRESS, "Sprawdzam wpływ stresu na sen"),
        (HYPOTHESIS_NAP, "Sprawdzam wpływ drzemek na nocny sen"),
        (HYPOTHESIS_ALCOHOL, "Sprawdzam wpływ alkoholu na sen"),
        (HYPOTHESIS_TRAINING, "Sprawdzam wpływ treningu na sen"),
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
        "Preferowane źródło synchronizacji",
        max_length=20,
        choices=PREFERRED_SYNC_SOURCE_CHOICES,
        default=SYNC_SOURCE_HEALTH_CONNECT,
    )
    active_hypothesis = models.CharField(
        "Aktywna hipoteza miesiąca",
        max_length=20,
        choices=HYPOTHESIS_CHOICES,
        blank=True,
        default=HYPOTHESIS_NONE,
    )
    active_hypothesis_started_at = models.DateField(
        "Data rozpoczęcia hipotezy",
        null=True,
        blank=True,
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


class Friendship(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_DECLINED = "declined"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Oczekuje"),
        (STATUS_ACCEPTED, "Znajomi"),
        (STATUS_DECLINED, "Odrzucone"),
    ]

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_friendships",
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_friendships",
    )
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING)
    responded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Relacja znajomych"
        verbose_name_plural = "Relacje znajomych"
        constraints = [
            models.UniqueConstraint(
                fields=("sender", "receiver"),
                name="accounts_friendship_unique_pair",
            ),
            models.CheckConstraint(
                condition=~models.Q(sender=models.F("receiver")),
                name="accounts_friendship_no_self_relation",
            ),
        ]

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username} ({self.get_status_display()})"

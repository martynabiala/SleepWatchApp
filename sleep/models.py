from django.conf import settings
from django.db import models
import secrets


class SleepRecord(models.Model):
    SOURCE_MANUAL_CSV = "manual_csv"
    SOURCE_MI_FITNESS = "mi_fitness"
    SOURCE_ZEPP_LIFE = "zepp_life"
    SOURCE_HEALTH_CONNECT = "health_connect"
    SOURCE_ZEPP_SYNC = "zepp_sync"

    SOURCE_CHOICES = [
        (SOURCE_MANUAL_CSV, "Import CSV"),
        (SOURCE_MI_FITNESS, "Import CSV"),
        (SOURCE_ZEPP_LIFE, "Import CSV"),
        (SOURCE_HEALTH_CONNECT, "Health Connect"),
        (SOURCE_ZEPP_SYNC, "Synchronizacja Zepp"),
    ]

    IMPORT_SOURCE_CHOICES = [
        (SOURCE_MANUAL_CSV, "Import CSV"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sleep_records",
    )
    source = models.CharField("Źródło", max_length=20, choices=SOURCE_CHOICES)
    sleep_date = models.DateField("Data nocy")
    bedtime = models.TimeField("Godzina zaśnięcia", null=True, blank=True)
    wake_time = models.TimeField("Godzina pobudki", null=True, blank=True)
    sleep_duration_minutes = models.PositiveIntegerField("Czas snu (min)")
    awakenings_count = models.PositiveSmallIntegerField("Liczba wybudzeń", null=True, blank=True)
    awake_minutes = models.PositiveIntegerField("Czas czuwania (min)", null=True, blank=True)
    light_sleep_minutes = models.PositiveIntegerField("Sen lekki (min)", null=True, blank=True)
    deep_sleep_minutes = models.PositiveIntegerField("Sen głęboki (min)", null=True, blank=True)
    rem_minutes = models.PositiveIntegerField("REM (min)", null=True, blank=True)
    avg_heart_rate = models.PositiveSmallIntegerField("Średnie tętno", null=True, blank=True)
    min_spo2 = models.PositiveSmallIntegerField("Minimalne SpO2", null=True, blank=True)
    raw_data = models.JSONField("Dane surowe", default=dict, blank=True)
    external_record_id = models.CharField("ID zewnętrznego rekordu", max_length=120, blank=True)
    synced_at = models.DateTimeField("Data synchronizacji", null=True, blank=True)
    device_name = models.CharField("Nazwa urządzenia", max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-sleep_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "source", "sleep_date"],
                name="unique_sleep_record_per_source_and_date",
            ),
            models.UniqueConstraint(
                fields=["user", "source", "external_record_id"],
                condition=~models.Q(external_record_id=""),
                name="unique_external_sleep_record_per_source",
            ),
        ]
        verbose_name = "Rekord snu"
        verbose_name_plural = "Rekordy snu"

    def __str__(self):
        return f"{self.user.username} - {self.sleep_date}"

    @property
    def sleep_duration_display(self):
        hours, minutes = divmod(self.sleep_duration_minutes, 60)
        return f"{hours}h {minutes:02d}m"


class ImportHistory(models.Model):
    SOURCE_MANUAL_CSV = SleepRecord.SOURCE_MANUAL_CSV
    SOURCE_MI_FITNESS = SleepRecord.SOURCE_MI_FITNESS
    SOURCE_ZEPP_LIFE = SleepRecord.SOURCE_ZEPP_LIFE
    SOURCE_CHOICES = SleepRecord.SOURCE_CHOICES
    IMPORT_SOURCE_CHOICES = SleepRecord.IMPORT_SOURCE_CHOICES

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sleep_imports",
    )
    source = models.CharField("Źródło", max_length=20, choices=SOURCE_CHOICES)
    file_name = models.CharField("Nazwa pliku", max_length=255)
    imported_at = models.DateTimeField("Data importu", auto_now_add=True)
    total_rows = models.PositiveIntegerField("Wszystkie wiersze", default=0)
    added_count = models.PositiveIntegerField("Dodane rekordy", default=0)
    duplicate_count = models.PositiveIntegerField("Duplikaty", default=0)
    error_count = models.PositiveIntegerField("Błędy", default=0)

    class Meta:
        ordering = ["-imported_at"]
        verbose_name = "Historia importu"
        verbose_name_plural = "Historie importów"

    def __str__(self):
        return f"{self.file_name} ({self.imported_at:%Y-%m-%d %H:%M})"


class SleepNote(models.Model):
    QUALITY_BAD = "bad"
    QUALITY_NEUTRAL = "neutral"
    QUALITY_GOOD = "good"

    TRAINING_NONE = "none"
    TRAINING_LIGHT = "light"
    TRAINING_MODERATE = "moderate"
    TRAINING_HARD = "hard"

    QUALITY_CHOICES = [
        (QUALITY_BAD, "Słaba"),
        (QUALITY_NEUTRAL, "Neutralna"),
        (QUALITY_GOOD, "Dobra"),
    ]

    TRAINING_CHOICES = [
        (TRAINING_NONE, "Brak"),
        (TRAINING_LIGHT, "Lekki"),
        (TRAINING_MODERATE, "Średni"),
        (TRAINING_HARD, "Ciężki"),
    ]

    sleep_record = models.OneToOneField(
        SleepRecord,
        on_delete=models.CASCADE,
        related_name="note",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sleep_notes",
    )
    sleep_quality = models.CharField(
        "Jakość snu",
        max_length=10,
        choices=QUALITY_CHOICES,
        default=QUALITY_NEUTRAL,
    )
    caffeine_used = models.BooleanField("Czy była kofeina", default=False)
    caffeine_last_time = models.TimeField("Godzina ostatniej dawki kofeiny", null=True, blank=True)
    caffeine_count = models.PositiveSmallIntegerField("Liczba wypitych napojów z kofeiną", null=True, blank=True)
    nap_taken = models.BooleanField("Czy była drzemka", default=False)
    nap_time = models.TimeField("Godzina drzemki", null=True, blank=True)
    alcohol = models.BooleanField("Alkohol", default=False)
    training_level = models.CharField(
        "Trening",
        max_length=10,
        choices=TRAINING_CHOICES,
        default=TRAINING_NONE,
    )
    training_done = models.BooleanField("Czy był trening", default=False)
    training_time = models.TimeField("Godzina treningu", null=True, blank=True)
    stress_level = models.PositiveSmallIntegerField("Poziom stresu", null=True, blank=True)
    note_text = models.TextField("Notatka", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Notatka do nocy"
        verbose_name_plural = "Notatki do nocy"

    def __str__(self):
        return f"Notatka: {self.sleep_record.sleep_date}"


class SleepSyncConnection(models.Model):
    PROVIDER_HEALTH_CONNECT = SleepRecord.SOURCE_HEALTH_CONNECT
    PROVIDER_ZEPP = SleepRecord.SOURCE_ZEPP_SYNC

    PROVIDER_CHOICES = [
        (PROVIDER_HEALTH_CONNECT, "Health Connect"),
        (PROVIDER_ZEPP, "Zepp"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sleep_sync_connections",
    )
    provider = models.CharField("Dostawca synchronizacji", max_length=30, choices=PROVIDER_CHOICES)
    is_enabled = models.BooleanField("Czy połączenie jest aktywne", default=True)
    last_synced_at = models.DateTimeField("Ostatnia synchronizacja", null=True, blank=True)
    last_imported_count = models.PositiveIntegerField("Liczba ostatnio pobranych rekordów", default=0)
    last_error = models.TextField("Ostatni błąd", blank=True)
    last_device_name = models.CharField("Ostatnie urządzenie", max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["provider"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "provider"],
                name="unique_sleep_sync_connection_per_provider",
            )
        ]
        verbose_name = "Połączenie synchronizacji snu"
        verbose_name_plural = "Połączenia synchronizacji snu"

    def __str__(self):
        return f"{self.user.username} - {self.get_provider_display()}"


class SleepApiToken(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sleep_api_token",
    )
    key = models.CharField("Klucz API", max_length=80, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used_at = models.DateTimeField("Ostatnie użycie", null=True, blank=True)

    class Meta:
        verbose_name = "Token API synchronizacji"
        verbose_name_plural = "Tokeny API synchronizacji"

    def __str__(self):
        return f"Token API {self.user.username}"

    @property
    def masked_key(self):
        if not self.key:
            return ""
        return f"{self.key[:6]}...{self.key[-4:]}"

    def rotate_key(self):
        self.key = secrets.token_urlsafe(32)
        return self.key

    def save(self, *args, **kwargs):
        if not self.key:
            self.rotate_key()
        super().save(*args, **kwargs)

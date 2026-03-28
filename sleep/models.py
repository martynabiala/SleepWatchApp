from django.conf import settings
from django.db import models


class SleepRecord(models.Model):
    SOURCE_MANUAL_CSV = "manual_csv"
    SOURCE_MI_FITNESS = "mi_fitness"
    SOURCE_ZEPP_LIFE = "zepp_life"

    MOVEMENT_LOW = "low"
    MOVEMENT_MEDIUM = "medium"
    MOVEMENT_HIGH = "high"
    MOVEMENT_UNKNOWN = "unknown"

    SOURCE_CHOICES = [
        (SOURCE_MANUAL_CSV, "Import CSV"),
        (SOURCE_MI_FITNESS, "Import CSV"),
        (SOURCE_ZEPP_LIFE, "Import CSV"),
    ]

    IMPORT_SOURCE_CHOICES = [
        (SOURCE_MANUAL_CSV, "Import CSV"),
    ]

    MOVEMENT_CHOICES = [
        (MOVEMENT_LOW, "Niski"),
        (MOVEMENT_MEDIUM, "Średni"),
        (MOVEMENT_HIGH, "Wysoki"),
        (MOVEMENT_UNKNOWN, "Brak danych"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sleep_records",
    )
    source = models.CharField("Źródło", max_length=20, choices=SOURCE_CHOICES)
    sleep_date = models.DateField("Data nocy")
    sleep_duration_minutes = models.PositiveIntegerField("Czas snu (min)")
    avg_heart_rate = models.PositiveSmallIntegerField("Średnie tętno", null=True, blank=True)
    min_heart_rate = models.PositiveSmallIntegerField("Minimalne tętno", null=True, blank=True)
    max_heart_rate = models.PositiveSmallIntegerField("Maksymalne tętno", null=True, blank=True)
    min_spo2 = models.PositiveSmallIntegerField("Minimalne SpO2", null=True, blank=True)
    movement_level = models.CharField(
        "Ruch/aktywność",
        max_length=20,
        choices=MOVEMENT_CHOICES,
        default=MOVEMENT_UNKNOWN,
    )
    raw_data = models.JSONField("Dane surowe", default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-sleep_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "source", "sleep_date"],
                name="unique_sleep_record_per_source_and_date",
            )
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
        verbose_name_plural = "Historia importów"

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
        (QUALITY_BAD, "Słaba noc"),
        (QUALITY_NEUTRAL, "Neutralna noc"),
        (QUALITY_GOOD, "Dobra noc"),
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
    caffeine_after_16 = models.BooleanField("Kofeina po 16:00", default=False)
    alcohol = models.BooleanField("Alkohol", default=False)
    training_level = models.CharField(
        "Trening",
        max_length=10,
        choices=TRAINING_CHOICES,
        default=TRAINING_NONE,
    )
    stress_level = models.PositiveSmallIntegerField("Poziom stresu", null=True, blank=True)
    note_text = models.TextField("Notatka", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Notatka do nocy"
        verbose_name_plural = "Notatki do nocy"

    def __str__(self):
        return f"Notatka: {self.sleep_record.sleep_date}"

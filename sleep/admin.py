from django.contrib import admin

from .models import ImportHistory, SleepNote, SleepRecord


@admin.register(SleepRecord)
class SleepRecordAdmin(admin.ModelAdmin):
    list_display = (
        "sleep_date",
        "user",
        "source",
        "sleep_duration_minutes",
        "avg_heart_rate",
        "min_spo2",
    )
    list_filter = ("source", "sleep_date")
    search_fields = ("user__username", "user__email")


@admin.register(ImportHistory)
class ImportHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "imported_at",
        "user",
        "file_name",
        "source",
        "added_count",
        "duplicate_count",
        "error_count",
    )
    list_filter = ("source", "imported_at")
    search_fields = ("user__username", "file_name")


@admin.register(SleepNote)
class SleepNoteAdmin(admin.ModelAdmin):
    list_display = (
        "sleep_record",
        "user",
        "sleep_quality",
        "training_level",
        "stress_level",
        "updated_at",
    )
    list_filter = ("sleep_quality", "training_level", "caffeine_used", "alcohol")
    search_fields = ("user__username", "sleep_record__sleep_date")

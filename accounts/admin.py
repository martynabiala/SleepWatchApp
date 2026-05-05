from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .models import BugReport, UserNotification, UserProfile

User = get_user_model()


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0
    fk_name = "user"


class SleepWatchUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = (
        "username",
        "email",
        "is_active",
        "is_staff",
        "date_joined",
    )
    search_fields = ("username", "email")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "avatar",
        "user",
        "age_group",
        "lifestyle",
        "sleep_goal_hours",
        "updated_at",
    )
    search_fields = ("display_name", "user__username", "user__email")
    list_filter = ("age_group", "lifestyle")


@admin.register(BugReport)
class BugReportAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "category",
        "status",
        "created_at",
    )
    list_filter = ("status", "category", "created_at")
    search_fields = (
        "description",
        "user__username",
        "user__email",
    )
    readonly_fields = ("user_agent", "created_at", "updated_at")
    fieldsets = (
        (
            "Zgłoszenie",
            {
                "fields": (
                    "user",
                    "category",
                    "status",
                    "description",
                )
            },
        ),
        (
            "Kontakt i kontekst",
            {
                "fields": (
                    "user_agent",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user",
        "kind",
        "is_read",
        "created_at",
    )
    list_filter = ("kind", "is_read", "created_at")
    search_fields = ("title", "body", "user__username", "user__email")
    readonly_fields = ("created_at", "read_at")


admin.site.unregister(User)
admin.site.register(User, SleepWatchUserAdmin)
admin.site.site_header = "SleepWatch Admin"
admin.site.site_title = "SleepWatch Admin"
admin.site.index_title = "Panel administratora"

from django.urls import reverse
from django.utils import timezone

from .models import UserNotification, create_user_notification


def resolve_daily_reminder_kind(now=None):
    local_now = timezone.localtime(now) if now is not None else timezone.localtime()
    hour = local_now.hour
    if 5 <= hour < 13:
        return "morning"
    if 17 <= hour <= 23:
        return "evening"
    return None


def get_daily_reminder_config(reminder_kind, reminder_date):
    date_part = reminder_date.isoformat()
    if reminder_kind == "morning":
        return {
            "title": "Poranny check-in",
            "body": "Oceń ostatnią noc i dopisz krótko, jak się dziś czujesz.",
            "action_url": reverse("morning_checkin"),
            "dedupe_key": f"daily-morning-{date_part}",
        }
    if reminder_kind == "evening":
        return {
            "title": "Wieczorne przypomnienie",
            "body": "Zamknij dzień krótkim check-inem i przygotuj spokojniejszy rytm przed snem.",
            "action_url": reverse("evening_checkin"),
            "dedupe_key": f"daily-evening-{date_part}",
        }
    raise ValueError("Unknown reminder kind.")


def create_daily_reminder_notification(user, reminder_kind, reminder_date=None):
    if reminder_date is None:
        reminder_date = timezone.localdate()

    config = get_daily_reminder_config(reminder_kind, reminder_date)
    already_exists = UserNotification.objects.filter(
        user=user,
        dedupe_key=config["dedupe_key"],
    ).exists()
    notification = create_user_notification(
        user,
        UserNotification.KIND_SLEEP,
        config["title"],
        config["body"],
        action_url=config["action_url"],
        dedupe_key=config["dedupe_key"],
    )
    return notification, not already_exists


def create_due_daily_reminder_for_user(user, now=None):
    if not user.is_active:
        return None, False

    reminder_kind = resolve_daily_reminder_kind(now)
    if reminder_kind is None:
        return None, False

    reminder_date = timezone.localdate(now) if now is not None else timezone.localdate()
    return create_daily_reminder_notification(user, reminder_kind, reminder_date)

from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserNotification, create_user_notification


class Command(BaseCommand):
    help = "Create daily morning or evening in-app reminder notifications."

    def add_arguments(self, parser):
        parser.add_argument(
            "--kind",
            choices=("morning", "evening", "auto"),
            default="auto",
            help="Reminder kind to create. Auto uses current local hour.",
        )
        parser.add_argument(
            "--date",
            help="Date for deduplication in YYYY-MM-DD format. Defaults to today.",
        )

    def handle(self, *args, **options):
        reminder_kind = options["kind"]
        reminder_date = self.get_reminder_date(options.get("date"))

        if reminder_kind == "auto":
            reminder_kind = self.resolve_auto_kind()

        config = self.get_reminder_config(reminder_kind, reminder_date)
        created_count = 0
        User = get_user_model()

        for user in User.objects.filter(is_active=True):
            already_exists = UserNotification.objects.filter(
                user=user,
                dedupe_key=config["dedupe_key"],
            ).exists()
            create_user_notification(
                user,
                UserNotification.KIND_SLEEP,
                config["title"],
                config["body"],
                action_url=config["action_url"],
                dedupe_key=config["dedupe_key"],
            )
            if not already_exists:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {created_count} {reminder_kind} reminder notification(s)."
            )
        )

    def get_reminder_date(self, raw_date):
        if not raw_date:
            return timezone.localdate()
        try:
            return datetime.strptime(raw_date, "%Y-%m-%d").date()
        except ValueError as exc:
            raise CommandError("Date must use YYYY-MM-DD format.") from exc

    def resolve_auto_kind(self):
        hour = timezone.localtime().hour
        if 5 <= hour < 13:
            return "morning"
        if 17 <= hour <= 23:
            return "evening"
        raise CommandError("Auto mode only creates reminders in morning or evening hours.")

    def get_reminder_config(self, reminder_kind, reminder_date):
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
        raise CommandError("Unknown reminder kind.")

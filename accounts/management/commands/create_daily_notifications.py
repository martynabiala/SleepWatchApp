from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.notifications import (
    create_daily_reminder_notification,
    resolve_daily_reminder_kind,
)


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
            reminder_kind = resolve_daily_reminder_kind()
            if reminder_kind is None:
                raise CommandError(
                    "Auto mode only creates reminders in morning or evening hours."
                )

        created_count = 0
        User = get_user_model()

        for user in User.objects.filter(is_active=True):
            _, created = create_daily_reminder_notification(
                user,
                reminder_kind,
                reminder_date,
            )
            if created:
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

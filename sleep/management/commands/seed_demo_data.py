import random
from datetime import date, datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import UserProfile
from sleep.models import ImportHistory, SleepNote, SleepRecord


class Command(BaseCommand):
    help = "Generuje demo dane uzytkownikow, snu, notatek i historii importu."

    def add_arguments(self, parser):
        parser.add_argument(
            "--users",
            type=int,
            default=3,
            help="Liczba demo uzytkownikow do przygotowania.",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=45,
            help="Liczba dni historii snu dla kazdego uzytkownika.",
        )
        parser.add_argument(
            "--password",
            type=str,
            default="SleepWatch123!",
            help="Haslo ustawiane demo uzytkownikom.",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Seed losowosci dla powtarzalnych danych.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        user_count = max(1, options["users"])
        days = max(7, options["days"])
        password = options["password"]
        random.seed(options["seed"])

        created_users = 0
        updated_records = 0
        created_records = 0

        for index in range(user_count):
            user, user_created = self._build_user(index=index, password=password)
            profile = self._build_profile(user=user, index=index)
            self._ensure_import_history(user=user)

            if user_created:
                created_users += 1

            created, updated = self._build_sleep_data(user=user, profile=profile, days=days, seed_offset=index)
            created_records += created
            updated_records += updated

        self.stdout.write(self.style.SUCCESS(
            f"Gotowe. Uzytkownicy utworzeni: {created_users}, rekordy dodane: {created_records}, rekordy zaktualizowane: {updated_records}."
        ))
        self.stdout.write(
            "Demo loginy: demo_anna, demo_bartek, demo_celina ... z haslem podanym w parametrze --password."
        )

    def _build_user(self, index, password):
        User = get_user_model()
        demos = [
            ("demo_anna", "anna@example.com", "Anna"),
            ("demo_bartek", "bartek@example.com", "Bartek"),
            ("demo_celina", "celina@example.com", "Celina"),
            ("demo_damian", "damian@example.com", "Damian"),
            ("demo_eliza", "eliza@example.com", "Eliza"),
            ("demo_filip", "filip@example.com", "Filip"),
        ]
        username, email, first_name = demos[index] if index < len(demos) else (
            f"demo_user_{index + 1}",
            f"demo_user_{index + 1}@example.com",
            f"Demo{index + 1}",
        )

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "first_name": first_name,
                "is_active": True,
            },
        )
        if not created:
            user.email = email
            user.first_name = first_name
            user.is_active = True

        user.set_password(password)
        user.save()
        return user, created

    def _build_profile(self, user, index):
        avatars = [
            UserProfile.AVATAR_MOON,
            UserProfile.AVATAR_STAR,
            UserProfile.AVATAR_CLOUD,
            UserProfile.AVATAR_SUN,
            UserProfile.AVATAR_LEAF,
            UserProfile.AVATAR_HEART,
        ]
        age_groups = [
            UserProfile.AGE_GROUP_UNDER_18,
            UserProfile.AGE_GROUP_18_25,
            UserProfile.AGE_GROUP_26_35,
            UserProfile.AGE_GROUP_36_50,
            UserProfile.AGE_GROUP_51_PLUS,
        ]
        lifestyles = [
            UserProfile.ACTIVITY_SEDENTARY,
            UserProfile.ACTIVITY_MODERATE,
            UserProfile.ACTIVITY_PHYSICAL_HIGH,
        ]

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.display_name = user.first_name or user.username
        profile.avatar = avatars[index % len(avatars)]
        profile.age_group = age_groups[index % len(age_groups)]
        profile.lifestyle = lifestyles[index % len(lifestyles)]
        profile.sleep_goal_hours = 7 + (index % 3)

        is_child_account = profile.age_group == UserProfile.AGE_GROUP_UNDER_18
        profile.is_child_account = is_child_account
        profile.parent_email = f"rodzic_{user.username}@example.com" if is_child_account else ""
        profile.parental_consent_granted = is_child_account
        profile.parental_consent_at = timezone.now() if is_child_account else None
        profile.save()
        return profile

    def _ensure_import_history(self, user):
        file_name = f"seeded-demo-{user.username}.csv"
        history = ImportHistory.objects.filter(user=user, file_name=file_name).first()
        if history:
            history.source = ImportHistory.SOURCE_MANUAL_CSV
            history.total_rows = 45
            history.added_count = 45
            history.duplicate_count = 0
            history.error_count = 0
            history.save(update_fields=["source", "total_rows", "added_count", "duplicate_count", "error_count"])
            return history

        return ImportHistory.objects.create(
            user=user,
            source=ImportHistory.SOURCE_MANUAL_CSV,
            file_name=file_name,
            total_rows=45,
            added_count=45,
            duplicate_count=0,
            error_count=0,
        )

    def _build_sleep_data(self, user, profile, days, seed_offset):
        created_records = 0
        updated_records = 0
        base_date = timezone.localdate()
        notes = [
            "Wieczor byl spokojny i bez ekranu przed snem.",
            "Pozna kolacja mogla pogorszyc jakosc snu.",
            "Dzien byl bardziej stresujacy niz zwykle.",
            "Krotki spacer wieczorem dobrze zadzialal.",
            "Po treningu zasniecie bylo szybsze.",
            "Drzemka po poludniu mogla skrocic noc.",
        ]

        for day_offset in range(days):
            sleep_date = base_date - timedelta(days=day_offset)
            rng = random.Random((seed_offset + 1) * 10_000 + day_offset)

            duration = max(320, min(560, int(rng.normalvariate(450 + seed_offset * 10, 38))))
            bedtime_minutes = 21 * 60 + 15 + rng.randint(0, 180)
            bedtime_dt = datetime.combine(date.today(), time.min) + timedelta(minutes=bedtime_minutes)
            bedtime = bedtime_dt.time().replace(second=0, microsecond=0)
            wake_dt = bedtime_dt + timedelta(minutes=duration + rng.randint(8, 35))
            wake_time = wake_dt.time().replace(second=0, microsecond=0)

            awake_minutes = rng.randint(8, 48)
            awakenings = rng.randint(0, 4)
            deep = int(duration * rng.uniform(0.16, 0.26))
            rem = int(duration * rng.uniform(0.18, 0.24))
            light = max(duration - deep - rem, 120)

            defaults = {
                "source": SleepRecord.SOURCE_MANUAL_CSV,
                "bedtime": bedtime,
                "wake_time": wake_time,
                "sleep_duration_minutes": duration,
                "awakenings_count": awakenings,
                "awake_minutes": awake_minutes,
                "light_sleep_minutes": light,
                "deep_sleep_minutes": deep,
                "rem_minutes": rem,
                "avg_heart_rate": rng.randint(52, 74),
                "min_spo2": rng.randint(91, 98),
                "raw_data": {
                    "seeded": True,
                    "goal_hours": profile.sleep_goal_hours,
                    "generated_at": timezone.now().isoformat(),
                },
            }

            record, created = SleepRecord.objects.update_or_create(
                user=user,
                source=SleepRecord.SOURCE_MANUAL_CSV,
                sleep_date=sleep_date,
                defaults=defaults,
            )

            if created:
                created_records += 1
            else:
                updated_records += 1

            self._build_note(user=user, record=record, day_offset=day_offset, rng=rng, notes=notes)

        return created_records, updated_records

    def _build_note(self, user, record, day_offset, rng, notes):
        quality = SleepNote.QUALITY_GOOD if record.sleep_duration_minutes >= 440 else (
            SleepNote.QUALITY_BAD if record.sleep_duration_minutes < 390 else SleepNote.QUALITY_NEUTRAL
        )

        caffeine_used = rng.random() < 0.35
        nap_taken = rng.random() < 0.22
        alcohol_used = rng.random() < 0.14
        training_done = rng.random() < 0.45

        training_level = SleepNote.TRAINING_NONE
        if training_done:
            training_level = rng.choice(
                [SleepNote.TRAINING_LIGHT, SleepNote.TRAINING_MODERATE, SleepNote.TRAINING_HARD]
            )

        defaults = {
            "user": user,
            "sleep_quality": quality,
            "caffeine_used": caffeine_used,
            "caffeine_last_time": time(hour=rng.randint(13, 19), minute=rng.choice([0, 15, 30, 45])) if caffeine_used else None,
            "caffeine_count": rng.randint(1, 3) if caffeine_used else None,
            "nap_taken": nap_taken,
            "nap_time": time(hour=rng.randint(13, 17), minute=rng.choice([0, 15, 30, 45])) if nap_taken else None,
            "alcohol": alcohol_used,
            "training_level": training_level,
            "training_done": training_done,
            "training_time": time(hour=rng.randint(16, 21), minute=rng.choice([0, 15, 30, 45])) if training_done else None,
            "stress_level": rng.randint(2, 9),
            "note_text": notes[day_offset % len(notes)],
        }

        SleepNote.objects.update_or_create(
            sleep_record=record,
            defaults=defaults,
        )

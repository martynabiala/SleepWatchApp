from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import ImportHistory, SleepNote, SleepRecord


class SleepModuleTests(TestCase):
    def setUp(self):
        self.user = self._create_user("sleepuser")
        self.client.login(username="sleepuser", password="BardzoMocneHaslo123!")

    def _create_user(self, username):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        return User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )

    def test_csv_import_creates_sleep_record_and_history(self):
        csv_content = (
            "sleep_date,sleep_duration_minutes,avg_heart_rate,min_heart_rate,"
            "max_heart_rate,min_spo2,movement_level\n"
            "2026-03-20,430,58,49,74,93,low\n"
        )
        uploaded_file = SimpleUploadedFile(
            "sleep.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(
            reverse("sleep_import"),
            {"source": "manual_csv", "file": uploaded_file},
            follow=True,
        )

        self.assertRedirects(response, reverse("sleep_import"))
        self.assertEqual(SleepRecord.objects.count(), 1)
        record = SleepRecord.objects.get()
        self.assertEqual(record.sleep_duration_minutes, 430)
        self.assertEqual(record.movement_level, SleepRecord.MOVEMENT_LOW)
        self.assertEqual(ImportHistory.objects.count(), 1)
        history = ImportHistory.objects.get()
        self.assertEqual(history.added_count, 1)
        self.assertEqual(history.duplicate_count, 0)

    def test_duplicate_record_is_counted_in_import_history(self):
        SleepRecord.objects.create(
            user=self.user,
            source="manual_csv",
            sleep_date="2026-03-20",
            sleep_duration_minutes=420,
            avg_heart_rate=57,
            movement_level=SleepRecord.MOVEMENT_LOW,
        )
        csv_content = (
            "sleep_date,sleep_duration_minutes,avg_heart_rate,min_heart_rate,"
            "max_heart_rate,min_spo2,movement_level\n"
            "2026-03-20,430,58,49,74,93,low\n"
        )
        uploaded_file = SimpleUploadedFile("dupe.csv", csv_content.encode("utf-8"))

        self.client.post(
            reverse("sleep_import"),
            {"source": "manual_csv", "file": uploaded_file},
            follow=True,
        )

        self.assertEqual(SleepRecord.objects.count(), 1)
        history = ImportHistory.objects.latest("imported_at")
        self.assertEqual(history.duplicate_count, 1)

    def test_import_treats_existing_night_with_other_source_as_duplicate(self):
        SleepRecord.objects.create(
            user=self.user,
            source="zepp_life",
            sleep_date="2026-03-20",
            sleep_duration_minutes=420,
            avg_heart_rate=57,
            movement_level=SleepRecord.MOVEMENT_LOW,
        )
        csv_content = (
            "sleep_date,sleep_duration_minutes,avg_heart_rate,min_heart_rate,"
            "max_heart_rate,min_spo2,movement_level\n"
            "2026-03-20,430,58,49,74,93,low\n"
        )
        uploaded_file = SimpleUploadedFile("dupe-cross-source.csv", csv_content.encode("utf-8"))

        self.client.post(
            reverse("sleep_import"),
            {"source": "manual_csv", "file": uploaded_file},
            follow=True,
        )

        self.assertEqual(SleepRecord.objects.count(), 1)
        history = ImportHistory.objects.latest("imported_at")
        self.assertEqual(history.duplicate_count, 1)

    def test_manual_sleep_add_creates_record(self):
        response = self.client.post(
            reverse("sleep_add"),
            {
                "sleep_date": "2026-03-26",
                "sleep_duration_minutes": 455,
                "avg_heart_rate": 58,
                "min_heart_rate": 49,
                "max_heart_rate": 73,
                "min_spo2": 94,
                "movement_level": SleepRecord.MOVEMENT_LOW,
            },
            follow=True,
        )

        record = SleepRecord.objects.get(sleep_date="2026-03-26")
        self.assertRedirects(response, reverse("sleep_detail", args=[record.pk]))
        self.assertEqual(record.user, self.user)
        self.assertEqual(record.sleep_duration_minutes, 455)

    def test_manual_sleep_add_rejects_duplicate_date(self):
        SleepRecord.objects.create(
            user=self.user,
            source="manual_csv",
            sleep_date="2026-03-26",
            sleep_duration_minutes=430,
            avg_heart_rate=57,
            movement_level=SleepRecord.MOVEMENT_LOW,
        )

        response = self.client.post(
            reverse("sleep_add"),
            {
                "sleep_date": "2026-03-26",
                "sleep_duration_minutes": 455,
                "avg_heart_rate": 58,
                "movement_level": SleepRecord.MOVEMENT_LOW,
            },
        )

        self.assertContains(response, "Masz już zapisaną noc dla tej daty.")

    def test_sleep_list_shows_user_records_only(self):
        other_user = self._create_user("otheruser")
        SleepRecord.objects.create(
            user=self.user,
            source="manual_csv",
            sleep_date="2026-03-20",
            sleep_duration_minutes=430,
            avg_heart_rate=58,
            movement_level=SleepRecord.MOVEMENT_LOW,
        )
        SleepRecord.objects.create(
            user=other_user,
            source="manual_csv",
            sleep_date="2026-03-21",
            sleep_duration_minutes=400,
            avg_heart_rate=61,
            movement_level=SleepRecord.MOVEMENT_MEDIUM,
        )

        response = self.client.get(reverse("sleep_list"))

        self.assertContains(response, "20.03.2026")
        self.assertNotContains(response, "21.03.2026")

    def test_sleep_detail_allows_saving_note(self):
        record = SleepRecord.objects.create(
            user=self.user,
            source="manual_csv",
            sleep_date="2026-03-22",
            sleep_duration_minutes=450,
            avg_heart_rate=56,
            movement_level=SleepRecord.MOVEMENT_LOW,
        )

        response = self.client.post(
            reverse("sleep_detail", args=[record.pk]),
            {
                "sleep_quality": "good",
                "caffeine_after_16": "on",
                "training_level": "light",
                "stress_level": 7,
                "note_text": "Spokojna noc.",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("sleep_detail", args=[record.pk]))
        note = SleepNote.objects.get(sleep_record=record)
        self.assertEqual(note.sleep_quality, "good")
        self.assertTrue(note.caffeine_after_16)
        self.assertEqual(note.stress_level, 7)
        self.assertEqual(note.note_text, "Spokojna noc.")

    def test_sleep_detail_rejects_stress_out_of_scale(self):
        record = SleepRecord.objects.create(
            user=self.user,
            source="manual_csv",
            sleep_date="2026-03-25",
            sleep_duration_minutes=430,
            avg_heart_rate=59,
            movement_level=SleepRecord.MOVEMENT_LOW,
        )

        response = self.client.post(
            reverse("sleep_detail", args=[record.pk]),
            {
                "sleep_quality": "neutral",
                "training_level": "none",
                "stress_level": 14,
                "note_text": "",
            },
        )

        self.assertContains(response, "mniejsza lub równa 10")

    def test_dashboard_shows_sleep_trends(self):
        SleepRecord.objects.create(
            user=self.user,
            source="manual_csv",
            sleep_date="2026-03-23",
            sleep_duration_minutes=420,
            avg_heart_rate=60,
            min_spo2=93,
            movement_level=SleepRecord.MOVEMENT_LOW,
        )
        record = SleepRecord.objects.create(
            user=self.user,
            source="manual_csv",
            sleep_date="2026-03-24",
            sleep_duration_minutes=480,
            avg_heart_rate=57,
            min_spo2=95,
            movement_level=SleepRecord.MOVEMENT_MEDIUM,
        )
        SleepNote.objects.create(
            user=self.user,
            sleep_record=record,
            sleep_quality="good",
        )

        response = self.client.get(reverse("dashboard"))

        self.assertContains(response, "Trendy 7 dni")
        self.assertContains(response, "7h 30m")
        self.assertContains(response, "1 / 0")

    def test_dashboard_shows_self_analysis_insights(self):
        today = timezone.localdate()

        for offset in range(7):
            record = SleepRecord.objects.create(
                user=self.user,
                source="manual_csv",
                sleep_date=today - timedelta(days=offset),
                sleep_duration_minutes=480,
                avg_heart_rate=56,
                min_spo2=95,
                movement_level=SleepRecord.MOVEMENT_LOW,
            )
            SleepNote.objects.create(
                user=self.user,
                sleep_record=record,
                sleep_quality="good",
                stress_level=3,
                caffeine_after_16=False,
            )

        for offset in range(7, 14):
            record = SleepRecord.objects.create(
                user=self.user,
                source="manual_csv",
                sleep_date=today - timedelta(days=offset),
                sleep_duration_minutes=360,
                avg_heart_rate=64,
                min_spo2=92,
                movement_level=SleepRecord.MOVEMENT_MEDIUM,
            )
            SleepNote.objects.create(
                user=self.user,
                sleep_record=record,
                sleep_quality="bad",
                stress_level=8,
                caffeine_after_16=True,
            )

        response = self.client.get(reverse("dashboard"))

        self.assertContains(response, "Analiza własnych danych")
        self.assertContains(response, "W ostatnim tygodniu śpisz dłużej")
        self.assertContains(response, "Kofeina po 16:00 może skracać sen")

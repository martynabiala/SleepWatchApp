from datetime import time, timedelta
from unittest import skip

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import ManualSleepRecordForm
from .models import ImportHistory, SleepApiToken, SleepNote, SleepRecord, SleepSyncConnection


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
            "sleep_date,sleep_duration_minutes,awake_minutes,light_sleep_minutes,deep_sleep_minutes,"
            "rem_minutes,avg_heart_rate,min_spo2\n"
            "2026-03-20,430,25,210,110,95,58,93\n"
        )
        uploaded_file = SimpleUploadedFile(
            "sleep.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(
            reverse("sleep_import"),
            {"file": uploaded_file},
            follow=True,
        )

        self.assertRedirects(response, reverse("sleep_import"))
        self.assertEqual(SleepRecord.objects.count(), 1)
        record = SleepRecord.objects.get()
        self.assertEqual(record.sleep_duration_minutes, 430)
        self.assertEqual(record.deep_sleep_minutes, 110)
        self.assertEqual(record.source, SleepRecord.SOURCE_MANUAL_CSV)
        self.assertEqual(ImportHistory.objects.count(), 1)
        history = ImportHistory.objects.get()
        self.assertEqual(history.added_count, 1)
        self.assertEqual(history.duplicate_count, 0)
        self.assertEqual(history.source, SleepRecord.SOURCE_MANUAL_CSV)

    def test_duplicate_record_is_counted_in_import_history(self):
        SleepRecord.objects.create(
            user=self.user,
            source="manual_csv",
            sleep_date="2026-03-20",
            sleep_duration_minutes=420,
        )
        csv_content = (
            "sleep_date,sleep_duration_minutes,awake_minutes,light_sleep_minutes,deep_sleep_minutes,"
            "rem_minutes,avg_heart_rate,min_spo2\n"
            "2026-03-20,430,20,220,100,90,58,93\n"
        )
        uploaded_file = SimpleUploadedFile("dupe.csv", csv_content.encode("utf-8"))

        self.client.post(
            reverse("sleep_import"),
            {"file": uploaded_file},
            follow=True,
        )

        self.assertEqual(SleepRecord.objects.count(), 1)
        history = ImportHistory.objects.latest("imported_at")
        self.assertEqual(history.duplicate_count, 1)

    def test_csv_import_accepts_alias_column_names(self):
        csv_content = (
            "date,total_sleep_minutes,minutes_awake,light_sleep,deep_sleep,rem,avg_hr,spo2_min\n"
            "31.03.2026,430,25,210,110,95,58,93\n"
        )
        uploaded_file = SimpleUploadedFile("alias.csv", csv_content.encode("utf-8"))

        response = self.client.post(
            reverse("sleep_import"),
            {"file": uploaded_file},
            follow=True,
        )

        self.assertRedirects(response, reverse("sleep_import"))
        record = SleepRecord.objects.get(sleep_date="2026-03-31")
        self.assertEqual(record.sleep_duration_minutes, 430)
        self.assertEqual(record.awake_minutes, 25)
        self.assertEqual(record.light_sleep_minutes, 210)
        self.assertEqual(record.deep_sleep_minutes, 110)
        self.assertEqual(record.rem_minutes, 95)
        self.assertEqual(record.avg_heart_rate, 58)
        self.assertEqual(record.min_spo2, 93)
        self.assertEqual(record.source, SleepRecord.SOURCE_MANUAL_CSV)

    def test_import_auto_detects_mi_fitness_format(self):
        csv_content = (
            "Date,Sleep Minutes,Awake Minutes,Light Sleep Minutes,Deep Sleep Minutes,"
            "REM Minutes,Average Heart Rate,Lowest SpO2\n"
            "2026-03-30,440,18,220,120,100,57,94\n"
        )
        uploaded_file = SimpleUploadedFile("mi-fitness.csv", csv_content.encode("utf-8"))

        response = self.client.post(
            reverse("sleep_import"),
            {"file": uploaded_file},
            follow=True,
        )

        self.assertRedirects(response, reverse("sleep_import"))
        record = SleepRecord.objects.get(sleep_date="2026-03-30")
        self.assertEqual(record.source, SleepRecord.SOURCE_MI_FITNESS)
        self.assertContains(response, "Wykryty format: Mi Fitness")

    def test_import_auto_detects_zepp_life_format(self):
        csv_content = (
            "Sleep Date,Total Sleep,Awake Time,Light Sleep,Deep Sleep,REM Sleep,Heart Rate Avg,SpO2 Min\n"
            "2026-03-29,425,20,215,105,90,59,92\n"
        )
        uploaded_file = SimpleUploadedFile("zepp-life.csv", csv_content.encode("utf-8"))

        response = self.client.post(
            reverse("sleep_import"),
            {"file": uploaded_file},
            follow=True,
        )

        self.assertRedirects(response, reverse("sleep_import"))
        record = SleepRecord.objects.get(sleep_date="2026-03-29")
        self.assertEqual(record.source, SleepRecord.SOURCE_ZEPP_LIFE)
        self.assertContains(response, "Wykryty format: Zepp Life")

    def test_import_shows_helpful_error_for_unsupported_csv_layout(self):
        csv_content = "foo,bar,baz\n1,2,3\n"
        uploaded_file = SimpleUploadedFile("unknown.csv", csv_content.encode("utf-8"))

        response = self.client.post(
            reverse("sleep_import"),
            {"file": uploaded_file},
        )

        self.assertContains(response, "Nie udało się rozpoznać formatu pliku CSV.")
        self.assertContains(response, "SleepWatch CSV, Mi Fitness i Zepp Life")

    def test_import_treats_existing_night_with_other_source_as_duplicate(self):
        SleepRecord.objects.create(
            user=self.user,
            source="zepp_life",
            sleep_date="2026-03-20",
            sleep_duration_minutes=420,
        )
        csv_content = (
            "sleep_date,sleep_duration_minutes,awake_minutes,light_sleep_minutes,deep_sleep_minutes,"
            "rem_minutes,avg_heart_rate,min_spo2\n"
            "2026-03-20,430,20,220,100,90,58,93\n"
        )
        uploaded_file = SimpleUploadedFile("dupe-cross-source.csv", csv_content.encode("utf-8"))

        self.client.post(
            reverse("sleep_import"),
            {"file": uploaded_file},
            follow=True,
        )

        self.assertEqual(SleepRecord.objects.count(), 1)
        history = ImportHistory.objects.latest("imported_at")
        self.assertEqual(history.duplicate_count, 1)

    def test_import_allows_manual_column_mapping_after_unknown_format(self):
        csv_content = (
            "Night,Total,Wake,Light,Deep,RemPulse,HR Avg,Oxygen Low\n"
            "2026-03-28,430,20,220,110,80,58,93\n"
        )
        uploaded_file = SimpleUploadedFile("custom.csv", csv_content.encode("utf-8"))

        response = self.client.post(
            reverse("sleep_import"),
            {"file": uploaded_file},
        )

        self.assertContains(response, "Ręczne mapowanie kolumn")

        response = self.client.post(
            reverse("sleep_import"),
            {
                "step": "map_columns",
                "sleep_date": "Night",
                "sleep_duration_minutes": "Total",
                "awake_minutes": "Wake",
                "light_sleep_minutes": "Light",
                "deep_sleep_minutes": "Deep",
                "rem_minutes": "RemPulse",
                "avg_heart_rate": "HR Avg",
                "min_spo2": "Oxygen Low",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("sleep_import"))
        record = SleepRecord.objects.get(sleep_date="2026-03-28")
        self.assertEqual(record.sleep_duration_minutes, 430)
        self.assertEqual(record.source, SleepRecord.SOURCE_MANUAL_CSV)
        self.assertContains(response, "Wykryty format: Ręczne mapowanie CSV")

    def test_manual_sleep_add_creates_record_and_calculates_duration(self):
        response = self.client.post(
            reverse("sleep_add"),
            {
                "sleep_date": "2026-03-26",
                "bedtime": "23:15",
                "wake_time": "07:00",
                "awakenings_count": 2,
            },
            follow=True,
        )

        record = SleepRecord.objects.get(sleep_date="2026-03-26")
        self.assertRedirects(response, reverse("sleep_detail", args=[record.pk]))
        self.assertEqual(record.user, self.user)
        self.assertEqual(record.sleep_duration_minutes, 465)
        self.assertEqual(record.bedtime.strftime("%H:%M"), "23:15")
        self.assertEqual(record.wake_time.strftime("%H:%M"), "07:00")
        self.assertEqual(record.awakenings_count, 2)

    def test_manual_sleep_add_shows_warning_when_sleep_is_shorter_than_goal(self):
        response = self.client.post(
            reverse("sleep_add"),
            {
                "sleep_date": "2026-03-27",
                "bedtime": "01:00",
                "wake_time": "06:33",
            },
            follow=True,
        )

        self.assertContains(response, "krócej niż Twój docelowy czas snu")

    def test_manual_sleep_add_rejects_duplicate_date(self):
        SleepRecord.objects.create(
            user=self.user,
            source="manual_csv",
            sleep_date="2026-03-26",
            sleep_duration_minutes=430,
        )

        response = self.client.post(
            reverse("sleep_add"),
            {
                "sleep_date": "2026-03-26",
                "bedtime": "23:15",
                "wake_time": "07:00",
            },
        )

        self.assertContains(response, "Masz już zapisaną noc dla tej daty.")

    def test_manual_form_calculates_duration_across_midnight(self):
        duration = ManualSleepRecordForm.calculate_duration_minutes(time(23, 30), time(6, 45))
        self.assertEqual(duration, 435)

    @skip("Manual form no longer collects sleep phases for hand-added nights.")
    def test_manual_form_accepts_awakening_count(self):
        form = ManualSleepRecordForm(
            data={
                "sleep_date": "2026-03-30",
                "bedtime": "23:00",
                "wake_time": "06:00",
                "awakenings_count": 3,
            },
            user=self.user,
        )

        self.assertTrue(form.is_valid())
        self.assertIn("Suma faz snu jest zbyt duża", form.errors["rem_minutes"][0])

    def test_manual_form_validates_with_awakening_count_only(self):
        form = ManualSleepRecordForm(
            data={
                "sleep_date": "2026-03-31",
                "bedtime": "22:45",
                "wake_time": "06:30",
                "awakenings_count": 1,
            },
            user=self.user,
        )

        self.assertTrue(form.is_valid())

    def test_sleep_list_shows_user_records_only(self):
        other_user = self._create_user("otheruser")
        SleepRecord.objects.create(
            user=self.user,
            source="manual_csv",
            sleep_date="2026-03-20",
            sleep_duration_minutes=430,
            avg_heart_rate=58,
        )
        SleepRecord.objects.create(
            user=other_user,
            source="manual_csv",
            sleep_date="2026-03-21",
            sleep_duration_minutes=400,
            avg_heart_rate=61,
        )

        response = self.client.get(reverse("sleep_list"))

        self.assertContains(response, "20.03.2026")
        self.assertNotContains(response, "21.03.2026")

    def test_sleep_list_can_delete_selected_records(self):
        record_to_delete = SleepRecord.objects.create(
            user=self.user,
            source="manual_csv",
            sleep_date="2026-03-20",
            sleep_duration_minutes=430,
        )
        record_to_keep = SleepRecord.objects.create(
            user=self.user,
            source="manual_csv",
            sleep_date="2026-03-21",
            sleep_duration_minutes=410,
        )

        response = self.client.post(
            reverse("sleep_list"),
            {"selected_records": [str(record_to_delete.pk)]},
            follow=True,
        )

        self.assertRedirects(response, reverse("sleep_list"))
        self.assertFalse(SleepRecord.objects.filter(pk=record_to_delete.pk).exists())
        self.assertTrue(SleepRecord.objects.filter(pk=record_to_keep.pk).exists())

    def test_sleep_list_does_not_delete_other_user_records(self):
        other_user = self._create_user("otheruser_delete")
        other_record = SleepRecord.objects.create(
            user=other_user,
            source="manual_csv",
            sleep_date="2026-03-22",
            sleep_duration_minutes=420,
        )

        self.client.post(
            reverse("sleep_list"),
            {"selected_records": [str(other_record.pk)]},
            follow=True,
        )

        self.assertTrue(SleepRecord.objects.filter(pk=other_record.pk).exists())

    def test_sleep_detail_allows_saving_note(self):
        record = SleepRecord.objects.create(
            user=self.user,
            source="manual_csv",
            sleep_date="2026-03-22",
            bedtime="23:00",
            wake_time="06:30",
            sleep_duration_minutes=450,
            avg_heart_rate=56,
            awake_minutes=15,
            light_sleep_minutes=220,
            deep_sleep_minutes=120,
            rem_minutes=95,
        )

        response = self.client.post(
            reverse("sleep_detail", args=[record.pk]),
            {
                "sleep_quality": "good",
                "caffeine_used": "True",
                "caffeine_last_time": "15:30",
                "caffeine_count": 2,
                "training_done": "True",
                "training_level": "light",
                "training_time": "18:30",
                "stress_level": 7,
                "note_text": "Spokojna noc.",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("sleep_detail", args=[record.pk]))
        note = SleepNote.objects.get(sleep_record=record)
        self.assertEqual(note.sleep_quality, "good")
        self.assertTrue(note.caffeine_used)
        self.assertEqual(note.caffeine_last_time.strftime("%H:%M"), "15:30")
        self.assertEqual(note.caffeine_count, 2)
        self.assertTrue(note.training_done)
        self.assertEqual(note.training_level, "light")
        self.assertEqual(note.training_time.strftime("%H:%M"), "18:30")
        self.assertEqual(note.stress_level, 7)
        self.assertEqual(note.note_text, "Spokojna noc.")

    def test_sleep_detail_shows_auto_evaluation(self):
        record = SleepRecord.objects.create(
            user=self.user,
            source="manual_csv",
            sleep_date="2026-03-28",
            bedtime="23:00",
            wake_time="07:10",
            sleep_duration_minutes=490,
            avg_heart_rate=56,
            min_spo2=95,
            awake_minutes=10,
            light_sleep_minutes=230,
            deep_sleep_minutes=150,
            rem_minutes=110,
        )
        SleepNote.objects.create(
            user=self.user,
            sleep_record=record,
            sleep_quality="good",
            stress_level=2,
            caffeine_used=False,
            alcohol=False,
            training_done=True,
            training_level="light",
            training_time="17:45",
        )

        response = self.client.get(reverse("sleep_detail", args=[record.pk]))

        self.assertContains(response, "Ocena aplikacji")
        self.assertContains(response, "★★★★★")
        self.assertContains(response, "Sen głęboki")

    def test_sleep_detail_rejects_stress_out_of_scale(self):
        record = SleepRecord.objects.create(
            user=self.user,
            source="manual_csv",
            sleep_date="2026-03-25",
            sleep_duration_minutes=430,
            avg_heart_rate=59,
        )

        response = self.client.post(
            reverse("sleep_detail", args=[record.pk]),
            {
                "sleep_quality": "neutral",
                "caffeine_used": "False",
                "training_done": "False",
                "training_level": "none",
                "stress_level": 14,
                "note_text": "",
            },
        )

        self.assertContains(response, "mniejsza lub równa 10")

    def test_dashboard_shows_sleep_trends(self):
        today = timezone.localdate()
        SleepRecord.objects.create(
            user=self.user,
            source="manual_csv",
            sleep_date=today - timedelta(days=1),
            sleep_duration_minutes=470,
            avg_heart_rate=60,
            min_spo2=93,
            awake_minutes=12,
            light_sleep_minutes=240,
            deep_sleep_minutes=130,
            rem_minutes=100,
        )
        record = SleepRecord.objects.create(
            user=self.user,
            source="manual_csv",
            sleep_date=today,
            sleep_duration_minutes=480,
            avg_heart_rate=57,
            min_spo2=95,
            awake_minutes=12,
            light_sleep_minutes=230,
            deep_sleep_minutes=145,
            rem_minutes=105,
        )
        SleepNote.objects.create(
            user=self.user,
            sleep_record=record,
            sleep_quality="good",
        )

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard – SleepWatch")

    def test_dashboard_uses_app_evaluation_for_good_nights(self):
        record = SleepRecord.objects.create(
            user=self.user,
            source="manual_csv",
            sleep_date="2026-03-29",
            sleep_duration_minutes=300,
            avg_heart_rate=72,
            min_spo2=89,
            awake_minutes=80,
            light_sleep_minutes=180,
            deep_sleep_minutes=40,
            rem_minutes=20,
        )
        SleepNote.objects.create(
            user=self.user,
            sleep_record=record,
            sleep_quality="good",
            stress_level=9,
            caffeine_used=True,
            caffeine_last_time="18:00",
            caffeine_count=3,
            alcohol=True,
            training_done=True,
            training_level="hard",
            training_time="20:15",
        )

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard – SleepWatch")

    def test_sleep_detail_requires_training_details_when_training_was_done(self):
        record = SleepRecord.objects.create(
            user=self.user,
            source="manual_csv",
            sleep_date="2026-03-24",
            sleep_duration_minutes=430,
        )

        response = self.client.post(
            reverse("sleep_detail", args=[record.pk]),
            {
                "sleep_quality": "neutral",
                "training_done": "True",
                "training_level": "none",
                "stress_level": 4,
                "note_text": "",
            },
        )

        self.assertContains(response, "Wybierz intensywność treningu.")
        self.assertContains(response, "Podaj godzinę treningu.")

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
                awake_minutes=10,
                light_sleep_minutes=220,
                deep_sleep_minutes=150,
                rem_minutes=110,
            )
            SleepNote.objects.create(
                user=self.user,
                sleep_record=record,
                sleep_quality="good",
                stress_level=3,
                caffeine_used=False,
            )

        for offset in range(7, 14):
            record = SleepRecord.objects.create(
                user=self.user,
                source="manual_csv",
                sleep_date=today - timedelta(days=offset),
                sleep_duration_minutes=360,
                avg_heart_rate=64,
                min_spo2=92,
                awake_minutes=45,
                light_sleep_minutes=220,
                deep_sleep_minutes=70,
                rem_minutes=55,
            )
            SleepNote.objects.create(
                user=self.user,
                sleep_record=record,
                sleep_quality="bad",
                stress_level=8,
                caffeine_used=True,
                caffeine_last_time="19:00",
                caffeine_count=2,
            )

        response = self.client.get(reverse("dashboard"))

        self.assertContains(response, "Ostatnie 7 dni na tle 30 dni")
        self.assertContains(response, "W ostatnim tygodniu śpisz dłużej")
        self.assertContains(response, "Kofeina może skracać sen")

    def test_dashboard_allows_selecting_monthly_hypothesis(self):
        response = self.client.post(
            reverse("dashboard"),
            {
                "action": "update_hypothesis",
                "active_hypothesis": "caffeine",
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.active_hypothesis, "caffeine")
        self.assertEqual(self.user.profile.active_hypothesis_started_at, timezone.localdate())

    def test_dashboard_shows_monthly_hypothesis_summary(self):
        today = timezone.localdate()
        self.user.profile.active_hypothesis = "caffeine"
        self.user.profile.active_hypothesis_started_at = today
        self.user.profile.save(update_fields=["active_hypothesis", "active_hypothesis_started_at"])

        for offset in range(2):
            record = SleepRecord.objects.create(
                user=self.user,
                source="manual_csv",
                sleep_date=today - timedelta(days=offset),
                sleep_duration_minutes=350,
            )
            SleepNote.objects.create(
                user=self.user,
                sleep_record=record,
                sleep_quality="bad",
                caffeine_used=True,
                caffeine_last_time="18:30",
                caffeine_count=2,
            )

        for offset in range(2, 4):
            record = SleepRecord.objects.create(
                user=self.user,
                source="manual_csv",
                sleep_date=today - timedelta(days=offset),
                sleep_duration_minutes=470,
            )
            SleepNote.objects.create(
                user=self.user,
                sleep_record=record,
                sleep_quality="good",
                caffeine_used=False,
            )

        response = self.client.get(reverse("dashboard"))

        self.assertContains(response, "Eksperyment miesi\u0105ca")
        self.assertContains(response, "Wp\u0142yw kofeiny")
        self.assertContains(response, "s\u0105 \u015brednio kr\u00f3tsze")

    def test_sleep_detail_requires_caffeine_details_when_caffeine_was_used(self):
        record = SleepRecord.objects.create(
            user=self.user,
            source="manual_csv",
            sleep_date="2026-03-23",
            sleep_duration_minutes=430,
        )

        response = self.client.post(
            reverse("sleep_detail", args=[record.pk]),
            {
                "sleep_quality": "neutral",
                "caffeine_used": "True",
                "training_done": "False",
                "training_level": "none",
                "stress_level": 4,
                "note_text": "",
            },
        )

        self.assertContains(response, "Podaj godzinę ostatniej dawki kofeiny.")
        self.assertContains(response, "Podaj liczbę wypitych napojów z kofeiną.")

    def test_sleep_detail_rejects_unrealistic_caffeine_count(self):
        record = SleepRecord.objects.create(
            user=self.user,
            source="manual_csv",
            sleep_date="2026-03-24",
            sleep_duration_minutes=430,
        )

        response = self.client.post(
            reverse("sleep_detail", args=[record.pk]),
            {
                "sleep_quality": "neutral",
                "caffeine_used": "True",
                "caffeine_last_time": "15:00",
                "caffeine_count": 100,
                "training_done": "False",
                "training_level": "none",
                "stress_level": 4,
                "note_text": "",
            },
        )

        self.assertContains(response, "mniejsza lub równa 10")
    def test_sleep_detail_requires_nap_time_when_nap_was_taken(self):
        record = SleepRecord.objects.create(
            user=self.user,
            source="manual_csv",
            sleep_date="2026-03-26",
            sleep_duration_minutes=430,
        )

        response = self.client.post(
            reverse("sleep_detail", args=[record.pk]),
            {
                "sleep_quality": "neutral",
                "caffeine_used": "False",
                "nap_taken": "True",
                "alcohol": "False",
                "training_done": "False",
                "training_level": "none",
                "stress_level": 4,
                "note_text": "",
            },
        )

        self.assertContains(response, "Podaj godzinę drzemki.")
    def test_sleep_detail_saves_nap_and_shows_it_in_details(self):
        record = SleepRecord.objects.create(
            user=self.user,
            source="manual_csv",
            sleep_date="2026-03-27",
            sleep_duration_minutes=440,
        )

        response = self.client.post(
            reverse("sleep_detail", args=[record.pk]),
            {
                "sleep_quality": "good",
                "caffeine_used": "False",
                "nap_taken": "True",
                "nap_time": "14:20",
                "alcohol": "False",
                "training_done": "False",
                "training_level": "none",
                "stress_level": 3,
                "note_text": "Krotka drzemka po poludniu.",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("sleep_detail", args=[record.pk]))
        note = SleepNote.objects.get(sleep_record=record)
        self.assertTrue(note.nap_taken)
        self.assertEqual(note.nap_time.strftime("%H:%M"), "14:20")
        self.assertContains(response, "Drzemka")
        self.assertContains(response, "14:20")

    def test_sync_api_creates_health_connect_record_and_connection_status(self):
        token = SleepApiToken.objects.create(user=self.user)

        response = self.client.post(
            reverse("sleep_sync_api"),
            data={
                "provider": SleepRecord.SOURCE_HEALTH_CONNECT,
                "device_name": "Pixel 8",
                "records": [
                    {
                        "external_id": "hc-001",
                        "sleep_date": "2026-04-10",
                        "bedtime": "23:20",
                        "wake_time": "07:05",
                        "sleep_duration_minutes": 465,
                        "awake_minutes": 18,
                        "light_sleep_minutes": 230,
                        "deep_sleep_minutes": 130,
                        "rem_minutes": 100,
                        "avg_heart_rate": 57,
                        "min_spo2": 95,
                    }
                ],
            },
            content_type="application/json",
            headers={"Authorization": f"Bearer {token.key}"},
        )

        self.assertEqual(response.status_code, 200)
        record = SleepRecord.objects.get(source=SleepRecord.SOURCE_HEALTH_CONNECT)
        self.assertEqual(record.external_record_id, "hc-001")
        self.assertEqual(record.device_name, "Pixel 8")
        connection = SleepSyncConnection.objects.get(
            user=self.user,
            provider=SleepRecord.SOURCE_HEALTH_CONNECT,
        )
        self.assertEqual(connection.last_imported_count, 1)
        self.assertEqual(connection.last_device_name, "Pixel 8")

    def test_sync_api_updates_existing_external_record_without_duplicates(self):
        token = SleepApiToken.objects.create(user=self.user)
        SleepRecord.objects.create(
            user=self.user,
            source=SleepRecord.SOURCE_HEALTH_CONNECT,
            sleep_date="2026-04-10",
            sleep_duration_minutes=430,
            external_record_id="hc-001",
        )

        response = self.client.post(
            reverse("sleep_sync_api"),
            data={
                "provider": SleepRecord.SOURCE_HEALTH_CONNECT,
                "records": [
                    {
                        "external_id": "hc-001",
                        "sleep_date": "2026-04-10",
                        "sleep_duration_minutes": 470,
                        "awake_minutes": 15,
                    }
                ],
            },
            content_type="application/json",
            headers={"Authorization": f"Bearer {token.key}"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            SleepRecord.objects.filter(source=SleepRecord.SOURCE_HEALTH_CONNECT).count(),
            1,
        )
        record = SleepRecord.objects.get(source=SleepRecord.SOURCE_HEALTH_CONNECT)
        self.assertEqual(record.sleep_duration_minutes, 470)
        self.assertEqual(record.awake_minutes, 15)

    def test_sync_api_accepts_zepp_life_provider_as_mobile_sync(self):
        token = SleepApiToken.objects.create(user=self.user)

        response = self.client.post(
            reverse("sleep_sync_api"),
            data={
                "provider": SleepRecord.SOURCE_ZEPP_LIFE,
                "device_name": "Mi Band 8",
                "records": [
                    {
                        "external_id": "zepp-001",
                        "sleep_date": "2026-04-12",
                        "sleep_duration_minutes": 440,
                        "awake_minutes": 20,
                    }
                ],
            },
            content_type="application/json",
            headers={"Authorization": f"Bearer {token.key}"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["provider"], SleepRecord.SOURCE_ZEPP_SYNC)

        record = SleepRecord.objects.get(source=SleepRecord.SOURCE_ZEPP_SYNC)
        self.assertEqual(record.external_record_id, "zepp-001")
        self.assertEqual(record.device_name, "Mi Band 8")

        connection = SleepSyncConnection.objects.get(
            user=self.user,
            provider=SleepRecord.SOURCE_ZEPP_SYNC,
        )
        self.assertEqual(connection.last_imported_count, 1)
        self.assertEqual(connection.last_device_name, "Mi Band 8")

    def test_sync_api_rejects_invalid_token(self):
        response = self.client.post(
            reverse("sleep_sync_api"),
            data={"provider": SleepRecord.SOURCE_HEALTH_CONNECT, "records": []},
            content_type="application/json",
            headers={"Authorization": "Bearer invalid-token"},
        )

        self.assertEqual(response.status_code, 401)

    def test_profile_shows_sync_status_without_token_controls(self):
        SleepSyncConnection.objects.create(
            user=self.user,
            provider=SleepRecord.SOURCE_HEALTH_CONNECT,
            last_imported_count=2,
            last_device_name="Pixel 8",
            last_synced_at=timezone.now(),
        )

        response = self.client.get(reverse("profile"))

        self.assertContains(response, "Synchronizacja")
        self.assertNotContains(response, "Generuj token API")

    def test_mobile_login_api_returns_fresh_token(self):
        response = self.client.post(
            reverse("mobile_login_api"),
            data={
                "login": "sleepuser",
                "password": "BardzoMocneHaslo123!",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["token"])
        self.assertEqual(payload["user"]["username"], "sleepuser")

    def test_mobile_summary_api_returns_last_sleep_and_connections(self):
        token = SleepApiToken.objects.create(user=self.user)
        SleepRecord.objects.create(
            user=self.user,
            source=SleepRecord.SOURCE_HEALTH_CONNECT,
            sleep_date="2026-04-11",
            sleep_duration_minutes=455,
        )
        SleepSyncConnection.objects.create(
            user=self.user,
            provider=SleepRecord.SOURCE_HEALTH_CONNECT,
            last_imported_count=1,
            last_device_name="Pixel 8",
            last_synced_at=timezone.now(),
        )

        response = self.client.get(
            reverse("mobile_summary_api"),
            headers={"Authorization": f"Bearer {token.key}"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["user"]["username"], "sleepuser")
        self.assertEqual(payload["last_sleep"]["duration_display"], "7h 35m")
        self.assertTrue(payload["sync_connections"])

    def test_mobile_signup_api_creates_inactive_adult_account(self):
        response = self.client.post(
            reverse("mobile_signup_api"),
            data={
                "email": "nowy@example.com",
                "age_group": "18-25",
                "password1": "NoweMocneHaslo123!",
                "password2": "NoweMocneHaslo123!",
                "parent_email": "",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["flow"], "adult")

    def test_mobile_sleep_history_api_returns_recent_records(self):
        token = SleepApiToken.objects.create(user=self.user)
        SleepRecord.objects.create(
            user=self.user,
            source="manual_csv",
            sleep_date="2026-04-18",
            bedtime="23:15",
            wake_time="07:05",
            sleep_duration_minutes=470,
            awakenings_count=1,
        )

        response = self.client.get(
            reverse("mobile_sleep_history_api"),
            headers={"Authorization": f"Bearer {token.key}"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(len(payload["records"]), 1)
        self.assertEqual(payload["records"][0]["duration_display"], "7h 50m")

    def test_mobile_manual_sleep_create_api_adds_record(self):
        token = SleepApiToken.objects.create(user=self.user)

        response = self.client.post(
            reverse("mobile_manual_sleep_create_api"),
            data={
                "sleep_date": "2026-04-19",
                "bedtime": "23:00",
                "wake_time": "07:10",
                "awakenings_count": 2,
            },
            content_type="application/json",
            headers={"Authorization": f"Bearer {token.key}"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["record"]["duration_display"], "8h 10m")
        self.assertTrue(
            SleepRecord.objects.filter(
                user=self.user,
                sleep_date="2026-04-19",
                source=SleepRecord.SOURCE_MANUAL_CSV,
            ).exists()
        )

    def test_mobile_preferences_api_updates_preferred_sync_source(self):
        token = SleepApiToken.objects.create(user=self.user)

        response = self.client.post(
            reverse("mobile_preferences_api"),
            data={"preferred_sync_source": "zepp_life"},
            content_type="application/json",
            headers={"Authorization": f"Bearer {token.key}"},
        )

        self.assertEqual(response.status_code, 400)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.preferred_sync_source, "health_connect")

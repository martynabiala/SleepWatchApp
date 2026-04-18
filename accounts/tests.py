from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import Friendship
from accounts.views import build_badges
from sleep.models import SleepNote, SleepRecord


User = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AccountsFlowTests(TestCase):
    def test_user_can_send_friend_request(self):
        sender = User.objects.create_user(
            username="martyna",
            email="martyna@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )
        target = User.objects.create_user(
            username="ania",
            email="ania@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )
        self.client.login(username="martyna", password="BardzoMocneHaslo123!")

        response = self.client.post(
            reverse("friends"),
            {"action": "send_request", "user_id": target.id},
            follow=True,
        )

        self.assertRedirects(response, reverse("friends"))
        self.assertTrue(
            Friendship.objects.filter(
                sender=sender,
                receiver=target,
                status=Friendship.STATUS_PENDING,
            ).exists()
        )

    def test_user_can_accept_friend_request(self):
        sender = User.objects.create_user(
            username="kama",
            email="kama@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )
        receiver = User.objects.create_user(
            username="ola",
            email="ola@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )
        friendship = Friendship.objects.create(sender=sender, receiver=receiver)
        self.client.login(username="ola", password="BardzoMocneHaslo123!")

        response = self.client.post(
            reverse("friends"),
            {"action": "accept_request", "friendship_id": friendship.id},
            follow=True,
        )

        friendship.refresh_from_db()
        self.assertRedirects(response, reverse("friends"))
        self.assertEqual(friendship.status, Friendship.STATUS_ACCEPTED)
        self.assertIsNotNone(friendship.responded_at)

    def test_friends_page_shows_accepted_friend(self):
        first = User.objects.create_user(
            username="marta",
            email="marta@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )
        second = User.objects.create_user(
            username="kasia",
            email="kasia@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )
        Friendship.objects.create(
            sender=first,
            receiver=second,
            status=Friendship.STATUS_ACCEPTED,
            responded_at=timezone.now(),
        )
        self.client.login(username="marta", password="BardzoMocneHaslo123!")

        response = self.client.get(reverse("friends"))

        self.assertContains(response, "Twoja lista znajomych")
        self.assertContains(response, "kasia")
        self.assertContains(response, reverse("friend_profile", args=["kasia"]))

    def test_user_can_open_friend_profile_and_see_badges(self):
        first = User.objects.create_user(
            username="ola_friend",
            email="ola_friend@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )
        second = User.objects.create_user(
            username="kasia_friend",
            email="kasia_friend@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )
        Friendship.objects.create(
            sender=first,
            receiver=second,
            status=Friendship.STATUS_ACCEPTED,
            responded_at=timezone.now(),
        )
        SleepRecord.objects.create(
            user=second,
            source="manual_csv",
            sleep_date="2026-04-01",
            sleep_duration_minutes=440,
        )
        self.client.login(username="ola_friend", password="BardzoMocneHaslo123!")

        response = self.client.get(reverse("friend_profile", args=["kasia_friend"]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Profil znajomego")
        self.assertContains(response, "kasia_friend")
        self.assertContains(response, "Pierwszy krok")
        self.assertContains(response, "1 zapisanych nocy")

    def test_user_cannot_open_profile_of_person_who_is_not_a_friend(self):
        viewer = User.objects.create_user(
            username="viewer_user",
            email="viewer@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )
        stranger = User.objects.create_user(
            username="stranger_user",
            email="stranger@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )
        self.client.login(username="viewer_user", password="BardzoMocneHaslo123!")

        response = self.client.get(reverse("friend_profile", args=["stranger_user"]))

        self.assertEqual(response.status_code, 404)

    def test_user_cannot_add_self_to_friends(self):
        user = User.objects.create_user(
            username="selfuser",
            email="self@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )
        self.client.login(username="selfuser", password="BardzoMocneHaslo123!")

        response = self.client.post(
            reverse("friends"),
            {"action": "send_request", "user_id": user.id},
            follow=True,
        )

        self.assertRedirects(response, reverse("friends"))
        self.assertFalse(Friendship.objects.exists())
        self.assertContains(response, "Nie mozna dodac samej siebie do znajomych.")

    def test_user_can_remove_friend(self):
        first = User.objects.create_user(
            username="ola_remove",
            email="ola_remove@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )
        second = User.objects.create_user(
            username="zosia_remove",
            email="zosia_remove@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )
        friendship = Friendship.objects.create(
            sender=first,
            receiver=second,
            status=Friendship.STATUS_ACCEPTED,
            responded_at=timezone.now(),
        )
        self.client.login(username="ola_remove", password="BardzoMocneHaslo123!")

        response = self.client.post(
            reverse("friends"),
            {"action": "remove_friend", "friendship_id": friendship.id},
            follow=True,
        )

        self.assertRedirects(response, reverse("friends"))
        self.assertFalse(Friendship.objects.filter(pk=friendship.id).exists())

    def test_new_sleep_views_are_available_for_logged_user(self):
        user = User.objects.create_user(
            username="hub_user",
            email="hub@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )
        self.client.login(username="hub_user", password="BardzoMocneHaslo123!")

        urls = [
            reverse("evening_checkin"),
            reverse("morning_checkin"),
            reverse("habits_center"),
            reverse("insights_journal"),
            reverse("sleep_library"),
        ]

        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

    def test_habits_and_insights_pages_show_note_based_content(self):
        user = User.objects.create_user(
            username="habit_user",
            email="habit@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )
        sleep_record = SleepRecord.objects.create(
            user=user,
            source="manual_csv",
            sleep_date="2026-04-10",
            sleep_duration_minutes=430,
            avg_heart_rate=58,
        )
        SleepNote.objects.create(
            user=user,
            sleep_record=sleep_record,
            sleep_quality=SleepNote.QUALITY_GOOD,
            caffeine_used=True,
            caffeine_last_time="17:30",
            caffeine_count=2,
            training_done=True,
            training_level=SleepNote.TRAINING_LIGHT,
            training_time="18:30",
            stress_level=3,
            note_text="Wieczorem pomogl spokojny spacer.",
        )
        self.client.login(username="habit_user", password="BardzoMocneHaslo123!")

        habits_response = self.client.get(reverse("habits_center"))
        insights_response = self.client.get(reverse("insights_journal"))

        self.assertContains(habits_response, "Centrum nawyk")
        self.assertContains(habits_response, "Kofeina")
        self.assertContains(insights_response, "Dziennik wniosk")
        self.assertContains(insights_response, "Wieczorem pomogl spokojny spacer.")

    def test_signup_sends_activation_email_and_creates_inactive_user(self):
        response = self.client.post(
            reverse("signup"),
            {
                "email": "jan@example.com",
                "age_group": "18-25",
                "parent_email": "",
                "password1": "BardzoMocneHaslo123!",
                "password2": "BardzoMocneHaslo123!",
            },
        )

        self.assertRedirects(response, f"{reverse('signup_done')}?flow=adult")
        user = User.objects.get(email="jan@example.com")
        self.assertFalse(user.is_active)
        self.assertEqual(user.profile.display_name, "jan")
        self.assertEqual(user.profile.avatar, "moon")
        self.assertFalse(user.profile.is_child_account)
        self.assertTrue(user.profile.parental_consent_granted)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("potwierdzenie adresu e-mail", mail.outbox[0].subject.lower())
        self.assertIn("jan@example.com", mail.outbox[0].to)

    def test_child_signup_sends_parental_consent_email(self):
        response = self.client.post(
            reverse("signup"),
            {
                "email": "mila@example.com",
                "age_group": "under_18",
                "parent_email": "rodzic@example.com",
                "password1": "BardzoMocneHaslo123!",
                "password2": "BardzoMocneHaslo123!",
            },
        )

        self.assertRedirects(response, f"{reverse('signup_done')}?flow=child")
        user = User.objects.get(email="mila@example.com")
        self.assertFalse(user.is_active)
        self.assertTrue(user.profile.is_child_account)
        self.assertEqual(user.profile.parent_email, "rodzic@example.com")
        self.assertFalse(user.profile.parental_consent_granted)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("zgoda rodzica", mail.outbox[0].subject.lower())
        self.assertEqual(mail.outbox[0].to, ["rodzic@example.com"])

    def test_child_signup_requires_parent_email(self):
        response = self.client.post(
            reverse("signup"),
            {
                "email": "miki@example.com",
                "age_group": "under_18",
                "parent_email": "",
                "password1": "BardzoMocneHaslo123!",
                "password2": "BardzoMocneHaslo123!",
            },
        )

        self.assertContains(response, "Dla konta dziecka podaj adres e-mail rodzica lub opiekuna.")

    def test_activation_link_activates_adult_user_and_logs_in(self):
        self.client.post(
            reverse("signup"),
            {
                "email": "adam@example.com",
                "age_group": "18-25",
                "parent_email": "",
                "password1": "BardzoMocneHaslo123!",
                "password2": "BardzoMocneHaslo123!",
            },
        )

        activation_email = mail.outbox[0].body
        path = activation_email.split("http://testserver", 1)[1].strip().splitlines()[0]
        response = self.client.get(path, follow=True)

        activated_user = User.objects.get(email="adam@example.com")
        self.assertTrue(activated_user.is_active)
        self.assertRedirects(response, reverse("dashboard"))

    def test_parental_consent_link_activates_child_account(self):
        self.client.post(
            reverse("signup"),
            {
                "email": "zosia@example.com",
                "age_group": "under_18",
                "parent_email": "opiekun@example.com",
                "password1": "BardzoMocneHaslo123!",
                "password2": "BardzoMocneHaslo123!",
            },
        )

        consent_email = mail.outbox[0].body
        path = consent_email.split("http://testserver", 1)[1].strip().splitlines()[0]
        response = self.client.get(path, follow=True)

        child_user = User.objects.get(email="zosia@example.com")
        self.assertTrue(child_user.is_active)
        self.assertTrue(child_user.profile.parental_consent_granted)
        self.assertIsNotNone(child_user.profile.parental_consent_at)
        self.assertRedirects(response, reverse("login"))

    def test_inactive_user_cannot_log_in(self):
        User.objects.create_user(
            username="ola",
            email="ola@example.com",
            password="BardzoMocneHaslo123!",
            is_active=False,
        )
        response = self.client.post(
            reverse("login"),
            {"username": "ola", "password": "BardzoMocneHaslo123!"},
        )
        self.assertContains(response, "Wprowad")
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_user_can_log_in_with_email_address(self):
        User.objects.create_user(
            username="maillogin",
            email="maillogin@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )

        response = self.client.post(
            reverse("login"),
            {"username": "maillogin@example.com", "password": "BardzoMocneHaslo123!"},
            follow=True,
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_logged_user_can_update_profile_without_changing_login_or_email(self):
        user = User.objects.create_user(
            username="ewa",
            email="ewa@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )
        self.client.login(username="ewa", password="BardzoMocneHaslo123!")

        response = self.client.post(
            reverse("profile"),
            {
                "username": "ewa",
                "display_name": "Ewa Pink",
                "avatar": "star",
                "age_group": "26-35",
                "lifestyle": "moderate",
                "sleep_goal_hours": 7,
            },
            follow=True,
        )

        user.refresh_from_db()
        self.assertRedirects(response, reverse("profile"))
        self.assertEqual(user.username, "ewa")
        self.assertEqual(user.email, "ewa@example.com")
        self.assertEqual(user.profile.display_name, "Ewa Pink")
        self.assertEqual(user.profile.avatar, "star")
        self.assertEqual(user.profile.age_group, "26-35")

    def test_profile_allows_changing_login(self):
        user = User.objects.create_user(
            username="startlogin",
            email="loginchange@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )
        self.client.login(username="startlogin", password="BardzoMocneHaslo123!")

        response = self.client.post(
            reverse("profile"),
            {
                "username": "nowylogin",
                "display_name": "Login Change",
                "avatar": "cloud",
                "age_group": "26-35",
                "lifestyle": "moderate",
                "sleep_goal_hours": 8,
            },
            follow=True,
        )

        user.refresh_from_db()
        self.assertRedirects(response, reverse("profile"))
        self.assertEqual(user.username, "nowylogin")
        self.assertEqual(user.profile.avatar, "cloud")

    def test_profile_accepts_under_18_age_group(self):
        user = User.objects.create_user(
            username="ola18",
            email="ola18@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )
        self.client.login(username="ola18", password="BardzoMocneHaslo123!")

        response = self.client.post(
            reverse("profile"),
            {
                "username": "ola18",
                "display_name": "Ola",
                "avatar": "heart",
                "age_group": "under_18",
                "lifestyle": "moderate",
                "sleep_goal_hours": 8,
            },
            follow=True,
        )

        user.refresh_from_db()
        self.assertRedirects(response, reverse("profile"))
        self.assertEqual(user.profile.age_group, "under_18")
        self.assertEqual(user.profile.avatar, "heart")

    def test_profile_page_shows_login_and_email_as_read_only_summary(self):
        user = User.objects.create_user(
            username="ania",
            email="ania@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )
        self.client.login(username="ania", password="BardzoMocneHaslo123!")

        response = self.client.get(reverse("profile"))

        self.assertContains(response, "Edytuj profil")
        self.assertContains(response, "Login")
        self.assertContains(response, "Adres e-mail")
        self.assertContains(response, "Awatar")
        self.assertNotContains(response, 'value="ania" readonly', html=False)
        self.assertNotContains(response, 'value="ania@example.com" readonly', html=False)

    def test_profile_page_defaults_to_preview_mode(self):
        user = User.objects.create_user(
            username="podglad",
            email="podglad@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )
        self.client.login(username="podglad", password="BardzoMocneHaslo123!")

        response = self.client.get(reverse("profile"))

        self.assertContains(response, "Edytuj profil")
        self.assertContains(response, "Podgląd profilu")
        self.assertContains(response, "Odznaki")
        self.assertNotContains(response, "Zapisz profil")

    def test_profile_page_shows_form_in_edit_mode(self):
        user = User.objects.create_user(
            username="edycja",
            email="edycja@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )
        self.client.login(username="edycja", password="BardzoMocneHaslo123!")

        response = self.client.get(f"{reverse('profile')}?edit=1")

        self.assertContains(response, "Zapisz profil")
        self.assertContains(response, "Wróć do profilu")

    def test_password_reset_sends_email(self):
        User.objects.create_user(
            username="marta",
            email="marta@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )

        response = self.client.post(
            reverse("password_reset"),
            {"email": "marta@example.com"},
        )

        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("reset hasła", mail.outbox[0].subject.lower())
        self.assertIn("/reset-hasla/", mail.outbox[0].body)

    def test_peer_sleep_page_shows_comparison_for_similar_users(self):
        user = User.objects.create_user(
            username="ola_peer",
            email="ola_peer@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )
        user.profile.age_group = "18-25"
        user.profile.lifestyle = "moderate"
        user.profile.save()
        SleepRecord.objects.create(
            user=user,
            source="manual_csv",
            sleep_date="2026-03-30",
            sleep_duration_minutes=450,
            awakenings_count=2,
        )

        peer = User.objects.create_user(
            username="peer_user",
            email="peer@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )
        peer.profile.age_group = "18-25"
        peer.profile.lifestyle = "moderate"
        peer.profile.save()
        SleepRecord.objects.create(
            user=peer,
            source="manual_csv",
            sleep_date="2026-03-30",
            sleep_duration_minutes=480,
            awakenings_count=1,
        )

        self.client.login(username="ola_peer", password="BardzoMocneHaslo123!")
        response = self.client.get(reverse("peer_sleep"))

        self.assertContains(response, "Porównanie z podobnymi użytkownikami")
        self.assertContains(response, "Średni czas snu")
        self.assertContains(response, "Średnia liczba wybudzeń")
    def test_empty_auto_created_notes_do_not_count_toward_badges(self):
        user = User.objects.create_user(
            username="badgecheck",
            email="badgecheck@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )
        self.client.login(username="badgecheck", password="BardzoMocneHaslo123!")

        for day in range(3):
            record = SleepRecord.objects.create(
                user=user,
                source="manual_csv",
                sleep_date=f"2026-03-2{day + 1}",
                sleep_duration_minutes=430,
            )
            self.client.get(reverse("sleep_detail", args=[record.pk]))

        badges = build_badges(SleepRecord.objects.filter(user=user).select_related("note"))
        observation_badge = badges[1]

        self.assertFalse(observation_badge["earned"])
    def test_sleep_analysis_page_supports_multiple_ranges(self):
        user = User.objects.create_user(
            username="analiza",
            email="analiza@example.com",
            password="BardzoMocneHaslo123!",
            is_active=True,
        )
        self.client.login(username="analiza", password="BardzoMocneHaslo123!")

        today = timezone.localdate()
        for day in range(100):
            SleepRecord.objects.create(
                user=user,
                source="manual_csv",
                sleep_date=today - timedelta(days=day),
                sleep_duration_minutes=420 + (day % 5) * 10,
                avg_heart_rate=55 + (day % 4),
            )

        response = self.client.get(reverse("sleep_analysis"), {"range": "90"})

        self.assertContains(response, "Analiza snu")
        self.assertContains(response, "90 dni")
        self.assertContains(response, "Wykres czasu snu")
        self.assertContains(response, "Wykres liczby wybudzeń")
        self.assertContains(response, "Wykres średniego tętna")

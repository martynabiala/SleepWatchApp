from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AccountsFlowTests(TestCase):
    def test_signup_sends_activation_email_and_creates_inactive_user(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "jan",
                "email": "jan@example.com",
                "password1": "BardzoMocneHaslo123!",
                "password2": "BardzoMocneHaslo123!",
            },
        )

        self.assertRedirects(response, reverse("signup_done"))
        user = User.objects.get(username="jan")
        self.assertFalse(user.is_active)
        self.assertEqual(user.profile.display_name, "jan")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("potwierdzenie adresu e-mail", mail.outbox[0].subject.lower())

    def test_activation_link_activates_user_and_logs_in(self):
        self.client.post(
            reverse("signup"),
            {
                "username": "adam",
                "email": "adam@example.com",
                "password1": "BardzoMocneHaslo123!",
                "password2": "BardzoMocneHaslo123!",
            },
        )

        activation_email = mail.outbox[0].body
        path = activation_email.split("http://testserver", 1)[1].strip().splitlines()[0]
        response = self.client.get(path, follow=True)

        activated_user = User.objects.get(username="adam")
        self.assertTrue(activated_user.is_active)
        self.assertRedirects(response, reverse("dashboard"))

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

    def test_logged_user_can_update_profile(self):
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
                "email": "ewa.nowa@example.com",
                "display_name": "Ewa Pink",
                "age_group": "26-35",
                "lifestyle": "moderate",
                "sleep_goal_hours": 7,
            },
            follow=True,
        )

        user.refresh_from_db()
        self.assertRedirects(response, reverse("profile"))
        self.assertEqual(user.email, "ewa.nowa@example.com")
        self.assertEqual(user.profile.display_name, "Ewa Pink")
        self.assertEqual(user.profile.age_group, "26-35")

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
        self.assertIn("reset hasla", mail.outbox[0].subject.lower())
        self.assertIn("/reset-hasla/", mail.outbox[0].body)

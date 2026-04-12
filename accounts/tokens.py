from django.contrib.auth.tokens import PasswordResetTokenGenerator


account_activation_token = PasswordResetTokenGenerator()


class ParentalConsentTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        profile = user.profile
        return (
            f"{user.pk}{timestamp}{user.is_active}"
            f"{profile.parent_email}{profile.parental_consent_granted}"
        )


parental_consent_token = ParentalConsentTokenGenerator()

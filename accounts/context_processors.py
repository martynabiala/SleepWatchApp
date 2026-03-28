from django.conf import settings


def app_settings(request):
    return {
        "email_delivery_mode": getattr(settings, "EMAIL_DELIVERY_MODE", "file"),
    }

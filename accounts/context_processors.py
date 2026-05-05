from django.conf import settings

from .models import UserNotification


def app_settings(request):
    context = {
        "email_delivery_mode": getattr(settings, "EMAIL_DELIVERY_MODE", "file"),
    }

    if request.user.is_authenticated:
        notifications = UserNotification.objects.filter(user=request.user)
        context.update(
            {
                "recent_notifications": notifications[:5],
                "unread_notifications_count": notifications.filter(is_read=False).count(),
            }
        )
    else:
        context.update(
            {
                "recent_notifications": [],
                "unread_notifications_count": 0,
            }
        )

    return context

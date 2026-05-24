from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme


class DemoAccountReadOnlyMiddleware:
    safe_methods = {"GET", "HEAD", "OPTIONS", "TRACE"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self.should_block(request):
            if request.path.startswith("/api/"):
                return JsonResponse({"detail": "Konto demo jest tylko do podglądu."}, status=403)

            messages.warning(request, "Konto demo jest tylko do podglądu. Zmiany nie zostały zapisane.")
            return redirect(self.get_next_url(request))

        return self.get_response(request)

    def should_block(self, request):
        user = getattr(request, "user", None)
        if request.method in self.safe_methods:
            return False
        if not user or not user.is_authenticated:
            return False
        if user.username != "demo_anna":
            return False

        allowed_paths = {
            reverse("logout"),
        }
        return request.path not in allowed_paths

    def get_next_url(self, request):
        fallback = reverse("dashboard")
        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or fallback
        if url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host(), *settings.ALLOWED_HOSTS},
            require_https=request.is_secure(),
        ):
            return next_url
        return fallback

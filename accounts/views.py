from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.core.mail import send_mail
from django.db.models import Avg, Count, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from datetime import date, timedelta

from sleep.models import SleepNote, SleepRecord

from .forms import (
    LoginForm,
    ProfileForm,
    SignupForm,
    SleepWatchPasswordResetForm,
    SleepWatchSetPasswordForm,
    UserUpdateForm,
)
from .tokens import account_activation_token

User = get_user_model()


class UserLoginView(LoginView):
    authentication_form = LoginForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    pass


class UserPasswordResetView(PasswordResetView):
    form_class = SleepWatchPasswordResetForm
    template_name = "accounts/password_reset_form.html"
    email_template_name = "accounts/emails/password_reset_email.txt"
    subject_template_name = "accounts/emails/password_reset_subject.txt"
    success_url = reverse_lazy("password_reset_done")


class UserPasswordResetDoneView(PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class UserPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    form_class = SleepWatchSetPasswordForm
    success_url = reverse_lazy("password_reset_complete")


class UserPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"


def home_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("login")


def signup_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_activation_email(request, user)
            return redirect("signup_done")
    else:
        form = SignupForm()

    return render(request, "accounts/signup.html", {"form": form})


def signup_done_view(request: HttpRequest) -> HttpResponse:
    return render(request, "accounts/signup_done.html")


def activate_account_view(
    request: HttpRequest, uidb64: str, token: str
) -> HttpResponse:
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save(update_fields=["is_active"])
        login(request, user)
        messages.success(request, "Adres e-mail zostal potwierdzony. Konto jest aktywne.")
        return redirect("dashboard")

    return render(request, "accounts/activation_invalid.html", status=400)


@login_required
def dashboard_view(request: HttpRequest) -> HttpResponse:
    profile = request.user.profile
    sleep_records = SleepRecord.objects.filter(user=request.user)
    last_sleep = sleep_records.order_by("-sleep_date").first()
    month_comparison = build_month_comparison(sleep_records)
    self_comparison = build_self_comparison(sleep_records)
    context = {
        "profile": profile,
        "profile_completion": calculate_profile_completion(profile),
        "last_sleep": last_sleep,
        "stats_7": build_sleep_stats(sleep_records, 7),
        "stats_30": build_sleep_stats(sleep_records, 30),
        "sleep_chart_7": build_line_chart(sleep_records, 7, "sleep_duration_minutes"),
        "hr_chart_7": build_line_chart(sleep_records, 7, "avg_heart_rate"),
        "month_comparison": month_comparison,
        "self_comparison": self_comparison,
        "self_insights": build_self_insights(sleep_records, profile, self_comparison),
    }
    return render(request, "accounts/dashboard.html", context)


@login_required
def profile_view(request: HttpRequest) -> HttpResponse:
    profile = request.user.profile

    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)
            user.email = user_form.cleaned_data["email"]
            user.save()
            profile_form.save()
            messages.success(request, "Profil zostal zaktualizowany.")
            return redirect("profile")
    else:
        user_form = UserUpdateForm(
            instance=request.user,
            initial={"email": request.user.email},
        )
        profile_form = ProfileForm(instance=profile)

    return render(
        request,
        "accounts/profile.html",
        {
            "user_form": user_form,
            "profile_form": profile_form,
            "profile": profile,
        },
    )


def send_activation_email(request: HttpRequest, user: User) -> None:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = account_activation_token.make_token(user)
    activation_link = request.build_absolute_uri(
        reverse_lazy("activate_account", kwargs={"uidb64": uid, "token": token})
    )
    message = render_to_string(
        "accounts/emails/activation_email.txt",
        {
            "user": user,
            "activation_link": activation_link,
        },
    )
    send_mail(
        subject="SleepWatch - potwierdzenie adresu e-mail",
        message=message,
        from_email=None,
        recipient_list=[user.email],
    )


def calculate_profile_completion(profile) -> int:
    fields = [
        bool(profile.display_name),
        bool(profile.age_group),
        bool(profile.lifestyle),
        bool(profile.sleep_goal_hours),
    ]
    return int((sum(fields) / len(fields)) * 100)


def build_sleep_stats(queryset, days):
    start_date = timezone.localdate() - timedelta(days=days - 1)
    records = queryset.filter(sleep_date__gte=start_date)
    total = records.count()
    aggregates = records.aggregate(
        avg_sleep=Avg("sleep_duration_minutes"),
        avg_hr=Avg("avg_heart_rate"),
        avg_spo2=Avg("min_spo2"),
        good_nights=Count("note", filter=Q(note__sleep_quality=SleepNote.QUALITY_GOOD)),
        bad_nights=Count("note", filter=Q(note__sleep_quality=SleepNote.QUALITY_BAD)),
    )
    avg_sleep = aggregates["avg_sleep"] or 0
    hours = int(avg_sleep // 60) if avg_sleep else 0
    minutes = int(avg_sleep % 60) if avg_sleep else 0
    return {
        "days": days,
        "total": total,
        "avg_sleep_display": f"{hours}h {minutes:02d}m" if total else "-",
        "avg_hr": round(aggregates["avg_hr"], 1) if aggregates["avg_hr"] is not None else "-",
        "avg_spo2": round(aggregates["avg_spo2"], 1) if aggregates["avg_spo2"] is not None else "-",
        "good_nights": aggregates["good_nights"] or 0,
        "bad_nights": aggregates["bad_nights"] or 0,
    }


def build_line_chart(queryset, days, field_name):
    end_date = timezone.localdate()
    start_date = end_date - timedelta(days=days - 1)
    records = list(
        queryset.filter(sleep_date__range=(start_date, end_date))
        .order_by("sleep_date")
        .values_list("sleep_date", field_name)
    )
    if not records:
        return None

    values = [value for _, value in records if value is not None]
    if not values:
        return None

    min_value = min(values)
    max_value = max(values)
    span = max(max_value - min_value, 1)
    width = 320
    height = 120
    padding = 18
    step = (width - 2 * padding) / max(len(records) - 1, 1)

    points = []
    labels = []
    for index, (record_date, value) in enumerate(records):
        x = padding + index * step
        y = height - padding
        if value is not None:
            y = height - padding - ((value - min_value) / span) * (height - 2 * padding)
            points.append(f"{x:.2f},{y:.2f}")
            labels.append(
                {
                    "x": round(x, 2),
                    "y": round(y, 2),
                    "value": round(value, 1) if isinstance(value, float) else value,
                    "date": record_date.strftime("%d.%m"),
                }
            )

    if not points:
        return None

    return {
        "points": " ".join(points),
        "labels": labels,
        "min_value": round(min_value, 1),
        "max_value": round(max_value, 1),
        "field_name": field_name,
    }


def build_month_comparison(queryset):
    today = timezone.localdate()
    current_start = today.replace(day=1)
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end.replace(day=1)

    current_stats = summarize_period(queryset, current_start, today)
    previous_stats = summarize_period(queryset, previous_start, previous_end)

    return {
        "current_label": current_start.strftime("%m.%Y"),
        "previous_label": previous_start.strftime("%m.%Y"),
        "current": current_stats,
        "previous": previous_stats,
        "delta_sleep": format_delta(
            current_stats["avg_sleep_minutes"], previous_stats["avg_sleep_minutes"], "min"
        ),
        "delta_hr": format_delta(
            current_stats["avg_hr"], previous_stats["avg_hr"], "bpm"
        ),
        "delta_good_nights": format_delta(
            current_stats["good_nights"], previous_stats["good_nights"], ""
        ),
    }


def build_self_comparison(queryset):
    today = timezone.localdate()
    last_7_start = today - timedelta(days=6)
    last_30_start = today - timedelta(days=29)

    stats_7 = summarize_period(queryset, last_7_start, today)
    stats_30 = summarize_period(queryset, last_30_start, today)

    sleep_delta = round(stats_7["avg_sleep_minutes"] - stats_30["avg_sleep_minutes"], 1)
    hr_delta = round(stats_7["avg_hr"] - stats_30["avg_hr"], 1)
    good_night_share_7 = round((stats_7["good_nights"] / stats_7["total"]) * 100, 1) if stats_7["total"] else 0
    good_night_share_30 = round((stats_30["good_nights"] / stats_30["total"]) * 100, 1) if stats_30["total"] else 0

    return {
        "last_7": stats_7,
        "last_30": stats_30,
        "delta_sleep_minutes": sleep_delta,
        "delta_sleep_display": format_minutes_delta(sleep_delta),
        "delta_hr": hr_delta,
        "delta_hr_display": format_delta(hr_delta, 0, "bpm"),
        "delta_good_night_share": round(good_night_share_7 - good_night_share_30, 1),
        "delta_good_night_share_display": format_delta(good_night_share_7 - good_night_share_30, 0, "pp"),
        "good_night_share_7": good_night_share_7,
        "good_night_share_30": good_night_share_30,
    }


def build_self_insights(queryset, profile, self_comparison):
    today = timezone.localdate()
    records_30 = queryset.filter(sleep_date__gte=today - timedelta(days=29))
    insights = []

    total_records = records_30.count()
    if total_records < 3:
        return [
            {
                "tone": "neutral",
                "title": "Za mało danych na pełną analizę",
                "body": "Zaimportuj jeszcze kilka nocy, a SleepWatch pokaże pierwsze wnioski o Twoim śnie.",
            }
        ]

    sleep_delta = self_comparison["delta_sleep_minutes"]
    if self_comparison["last_7"]["total"] >= 3 and self_comparison["last_30"]["total"] >= 7:
        if sleep_delta >= 15:
            insights.append(
                {
                    "tone": "positive",
                    "title": "W ostatnim tygodniu śpisz dłużej",
                    "body": f"W ostatnich 7 dniach śpisz średnio o {minutes_delta_text(sleep_delta)} dłużej niż w ujęciu 30-dniowym.",
                }
            )
        elif sleep_delta <= -15:
            insights.append(
                {
                    "tone": "warning",
                    "title": "W ostatnim tygodniu śpisz krócej",
                    "body": f"W ostatnich 7 dniach śpisz średnio o {minutes_delta_text(abs(sleep_delta))} krócej niż zwykle.",
                }
            )

    goal_minutes = (profile.sleep_goal_hours or 0) * 60
    avg_sleep_7 = self_comparison["last_7"]["avg_sleep_minutes"]
    if goal_minutes and self_comparison["last_7"]["total"] >= 3:
        diff_to_goal = round(avg_sleep_7 - goal_minutes, 1)
        if diff_to_goal >= 15:
            insights.append(
                {
                    "tone": "positive",
                    "title": "Realizujesz swój cel snu",
                    "body": f"Średnia z ostatnich 7 dni jest o {minutes_delta_text(diff_to_goal)} wyższa niż Twój docelowy czas snu.",
                }
            )
        elif diff_to_goal <= -15:
            insights.append(
                {
                    "tone": "warning",
                    "title": "Zbyt krótki sen",
                    "body": f"W ostatnich 7 dniach śpisz średnio o {minutes_delta_text(abs(diff_to_goal))} mniej niż zakładany cel.",
                }
            )

    note_records = records_30.filter(note__isnull=False)
    caffeine_insight = build_boolean_factor_insight(
        note_records,
        "note__caffeine_after_16",
        "Kofeina po 16:00 może skracać sen",
        "Noce po kofeinie po 16:00 są średnio krótsze o {delta}.",
    )
    if caffeine_insight:
        insights.append(caffeine_insight)

    stress_insight = build_stress_insight(note_records)
    if stress_insight:
        insights.append(stress_insight)

    quality_insight = build_quality_insight(note_records)
    if quality_insight:
        insights.append(quality_insight)

    if not insights:
        insights.append(
            {
                "tone": "neutral",
                "title": "Na razie sen wygląda dość stabilnie",
                "body": "W ostatnich danych nie widać jeszcze wyraźnego wzorca związanego z czasem snu lub notatkami.",
            }
        )

    return insights[:4]


def build_boolean_factor_insight(queryset, field_name, title, body_template):
    with_factor = queryset.filter(**{field_name: True})
    without_factor = queryset.filter(**{field_name: False})

    if with_factor.count() < 2 or without_factor.count() < 2:
        return None

    avg_with = with_factor.aggregate(avg=Avg("sleep_duration_minutes"))["avg"] or 0
    avg_without = without_factor.aggregate(avg=Avg("sleep_duration_minutes"))["avg"] or 0
    delta = round(avg_without - avg_with, 1)

    if delta < 20:
        return None

    return {
        "tone": "warning",
        "title": title,
        "body": body_template.format(delta=minutes_delta_text(delta)),
    }


def build_stress_insight(queryset):
    high_stress = queryset.filter(note__stress_level__gte=7)
    low_stress = queryset.filter(note__stress_level__lte=4)

    if high_stress.count() < 2 or low_stress.count() < 2:
        return None

    avg_high = high_stress.aggregate(avg=Avg("sleep_duration_minutes"))["avg"] or 0
    avg_low = low_stress.aggregate(avg=Avg("sleep_duration_minutes"))["avg"] or 0
    delta = round(avg_low - avg_high, 1)

    if delta < 20:
        return None

    return {
        "tone": "warning",
        "title": "Stres może wpływać na pogorszenie jakości snu",
        "body": f"Wysoki stres wiąże się u Ciebie ze snem krótszym średnio o {minutes_delta_text(delta)}.",
    }


def build_quality_insight(queryset):
    total_notes = queryset.count()
    if total_notes < 4:
        return None

    good_nights = queryset.filter(note__sleep_quality=SleepNote.QUALITY_GOOD).count()
    bad_nights = queryset.filter(note__sleep_quality=SleepNote.QUALITY_BAD).count()
    good_share = good_nights / total_notes
    bad_share = bad_nights / total_notes

    if good_share >= 0.6:
        return {
            "tone": "positive",
            "title": "Przeważają dobre noce",
            "body": f"{good_nights} z {total_notes} ocenionych nocy oznaczyłaś jako dobre, więc trend wygląda obiecująco.",
        }

    if bad_share >= 0.5:
        return {
            "tone": "warning",
            "title": "Coraz więcej słabszych nocy",
            "body": f"{bad_nights} z {total_notes} ocenionych nocy oznaczyłaś jako słabe. Warto sprawdzić poziom stresu, kofeiny i regularność snu.",
        }

    return None


def summarize_period(queryset, start_date: date, end_date: date):
    records = queryset.filter(sleep_date__range=(start_date, end_date))
    total = records.count()
    aggregates = records.aggregate(
        avg_sleep=Avg("sleep_duration_minutes"),
        avg_hr=Avg("avg_heart_rate"),
        good_nights=Count("note", filter=Q(note__sleep_quality=SleepNote.QUALITY_GOOD)),
    )
    avg_sleep_minutes = round(aggregates["avg_sleep"] or 0, 1)
    return {
        "total": total,
        "avg_sleep_minutes": avg_sleep_minutes,
        "avg_sleep_display": minutes_to_display(avg_sleep_minutes) if total else "-",
        "avg_hr": round(aggregates["avg_hr"], 1) if aggregates["avg_hr"] is not None else 0,
        "avg_hr_display": round(aggregates["avg_hr"], 1) if aggregates["avg_hr"] is not None else "-",
        "good_nights": aggregates["good_nights"] or 0,
    }


def minutes_to_display(value):
    hours = int(value // 60)
    minutes = int(value % 60)
    return f"{hours}h {minutes:02d}m"


def minutes_delta_text(value):
    rounded_value = int(round(value))
    hours, minutes = divmod(abs(rounded_value), 60)
    parts = []
    if hours:
        parts.append(f"{hours} h")
    if minutes:
        parts.append(f"{minutes} min")
    return " ".join(parts) if parts else "0 min"


def format_minutes_delta(value):
    if not value:
        return "-"
    prefix = "+" if value > 0 else "-"
    return f"{prefix}{minutes_delta_text(value)}"


def format_delta(current, previous, suffix):
    if not previous and not current:
        return "-"
    delta = round(current - previous, 1)
    prefix = "+" if delta > 0 else ""
    suffix_part = f" {suffix}" if suffix else ""
    return f"{prefix}{delta}{suffix_part}"

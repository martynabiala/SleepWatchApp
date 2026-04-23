from datetime import date, timedelta
import json

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login
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
from django.db.models import Avg, Q
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from sleep.models import ImportHistory, SleepApiToken, SleepNote, SleepRecord, SleepSyncConnection
from sleep.services import build_sleep_auto_evaluation, get_sleep_api_token

from .forms import (
    LoginForm,
    MonthlyHypothesisForm,
    ProfileForm,
    SignupForm,
    SleepWatchPasswordResetForm,
    SleepWatchSetPasswordForm,
    SyncSourceSelectionForm,
    UserUpdateForm,
)
from .models import Friendship, UserProfile
from .tokens import account_activation_token, parental_consent_token

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
    return render(request, "home.html")


def signup_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            if user.profile.is_child_account:
                send_parental_consent_email(request, user)
                return redirect(f"{reverse_lazy('signup_done')}?flow=child")
            send_activation_email(request, user)
            return redirect(f"{reverse_lazy('signup_done')}?flow=adult")
    else:
        form = SignupForm()

    return render(request, "accounts/signup.html", {"form": form})


def signup_done_view(request: HttpRequest) -> HttpResponse:
    flow = request.GET.get("flow", "adult")
    return render(request, "accounts/signup_done.html", {"signup_flow": flow})


def activate_account_view(request: HttpRequest, uidb64: str, token: str) -> HttpResponse:
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user and not user.profile.is_child_account and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save(update_fields=["is_active"])
        login(request, user)
        messages.success(request, "Adres e-mail został potwierdzony. Konto jest aktywne.")
        return redirect("dashboard")

    return render(request, "accounts/activation_invalid.html", status=400)


def activate_child_account_view(request: HttpRequest, uidb64: str, token: str) -> HttpResponse:
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if (
        user
        and user.profile.is_child_account
        and parental_consent_token.check_token(user, token)
    ):
        profile = user.profile
        profile.parental_consent_granted = True
        profile.parental_consent_at = timezone.now()
        user.is_active = True
        user.save(update_fields=["is_active"])
        profile.save(update_fields=["parental_consent_granted", "parental_consent_at"])
        messages.success(
            request,
            "Zgoda rodzica została potwierdzona. Konto dziecka jest aktywne.",
        )
        return redirect("login")

    return render(request, "accounts/activation_invalid.html", status=400)


@login_required
def dashboard_view(request: HttpRequest) -> HttpResponse:
    profile = request.user.profile

    if request.method == "POST" and request.POST.get("action") == "update_hypothesis":
        previous_hypothesis = profile.active_hypothesis
        hypothesis_form = MonthlyHypothesisForm(request.POST, instance=profile)
        if hypothesis_form.is_valid():
            new_hypothesis = hypothesis_form.cleaned_data["active_hypothesis"]
            profile.active_hypothesis = new_hypothesis
            if new_hypothesis != previous_hypothesis:
                profile.active_hypothesis_started_at = timezone.localdate() if new_hypothesis else None
            profile.save(update_fields=["active_hypothesis", "active_hypothesis_started_at", "updated_at"])

            if profile.active_hypothesis:
                messages.success(request, "Zapisałyśmy aktywną hipotezę miesiąca.")
            else:
                messages.success(request, "Aktywna hipoteza została wyłączona.")
            return redirect("dashboard")
    else:
        hypothesis_form = MonthlyHypothesisForm(instance=profile)

    sleep_records = SleepRecord.objects.filter(user=request.user).select_related("user", "note")
    last_sleep = sleep_records.order_by("-sleep_date").first()

    last_sleep_note = None
    last_sleep_evaluation = None
    if last_sleep:
        try:
            last_sleep_note = last_sleep.note
        except SleepNote.DoesNotExist:
            last_sleep_note = None
        last_sleep_evaluation = build_sleep_auto_evaluation(last_sleep, last_sleep_note, profile)

    profile_completion = calculate_profile_completion(profile, request.user)
    stats_7 = build_sleep_stats(sleep_records, 7)
    stats_30 = build_sleep_stats(sleep_records, 30)
    month_comparison = build_month_comparison(sleep_records)
    self_comparison = build_self_comparison(sleep_records)
    weekly_goal = build_weekly_goal(sleep_records)
    self_insights = build_self_insights(sleep_records, profile, self_comparison)

    context = {
        "profile": profile,
        "profile_completion": profile_completion,
        "last_sleep": last_sleep,
        "last_sleep_note": last_sleep_note,
        "last_sleep_evaluation": last_sleep_evaluation,
        "stats_7": stats_7,
        "stats_30": stats_30,
        "sleep_chart_7": build_chart_series(sleep_records, 7, "sleep_duration_minutes"),
        "hr_chart_7": build_chart_series(sleep_records, 7, "avg_heart_rate"),
        "month_comparison": month_comparison,
        "self_comparison": self_comparison,
        "self_insights": self_insights,
        "self_insight_titles": [insight["title"] for insight in self_insights],
        "peer_comparison": build_peer_comparison(request.user, profile),
        "sleep_streak": build_sleep_streak(sleep_records),
        "weekly_goal": weekly_goal,
        "dashboard_tip": build_dashboard_tip(
            last_sleep_evaluation,
            profile_completion,
            stats_7,
        ),
        "hypothesis_form": hypothesis_form,
        "experiment_heading": "Eksperyment miesiąca",
        "active_hypothesis_summary": build_active_hypothesis_summary(sleep_records, profile),
        "dashboard_alerts": build_dashboard_alerts(
            sleep_records,
            profile,
            profile_completion,
            weekly_goal,
        ),
    }
    return render(request, "accounts/dashboard.html", context)


@login_required
def analysis_view(request: HttpRequest) -> HttpResponse:
    profile = request.user.profile
    sleep_records = SleepRecord.objects.filter(user=request.user).select_related("user", "note")

    range_options = {
        "30": {"days": 30, "label": "30 dni"},
        "90": {"days": 90, "label": "90 dni"},
        "365": {"days": 365, "label": "Ostatni rok"},
    }

    selected_range = request.GET.get("range", "30")
    if selected_range not in range_options:
        selected_range = "30"

    selected_option = range_options[selected_range]
    selected_days = selected_option["days"]

    context = {
        "profile": profile,
        "range_options": [
            {"value": value, "label": option["label"]}
            for value, option in range_options.items()
        ],
        "selected_range": selected_range,
        "selected_range_label": selected_option["label"],
        "analysis_stats": build_sleep_stats(sleep_records, selected_days),
        "sleep_chart": build_chart_series(sleep_records, selected_days, "sleep_duration_minutes"),
        "hr_chart": build_chart_series(sleep_records, selected_days, "avg_heart_rate"),
        "awakenings_chart": build_chart_series(sleep_records, selected_days, "awakenings_count"),
    }
    return render(request, "accounts/sleep_analysis.html", context)


def get_user_sleep_records(user):
    return SleepRecord.objects.filter(user=user).select_related("user", "note")


def get_last_sleep_note(last_sleep):
    if last_sleep is None:
        return None
    try:
        return last_sleep.note
    except SleepNote.DoesNotExist:
        return None


def is_sleep_note_effectively_empty(note):
    if note is None:
        return True

    return (
        note.sleep_quality == SleepNote.QUALITY_NEUTRAL
        and not note.caffeine_used
        and note.caffeine_last_time is None
        and note.caffeine_count is None
        and not note.nap_taken
        and note.nap_time is None
        and not note.alcohol
        and not note.training_done
        and note.training_level == SleepNote.TRAINING_NONE
        and note.training_time is None
        and note.stress_level is None
        and not (note.note_text or "").strip()
    )


def build_filled_note_query(prefix: str = "note__"):
    return (
        ~Q(**{f"{prefix}sleep_quality": SleepNote.QUALITY_NEUTRAL})
        | Q(**{f"{prefix}caffeine_used": True})
        | Q(**{f"{prefix}caffeine_last_time__isnull": False})
        | Q(**{f"{prefix}caffeine_count__isnull": False})
        | Q(**{f"{prefix}nap_taken": True})
        | Q(**{f"{prefix}nap_time__isnull": False})
        | Q(**{f"{prefix}alcohol": True})
        | Q(**{f"{prefix}training_done": True})
        | ~Q(**{f"{prefix}training_level": SleepNote.TRAINING_NONE})
        | Q(**{f"{prefix}training_time__isnull": False})
        | Q(**{f"{prefix}stress_level__isnull": False})
        | ~Q(**{f"{prefix}note_text": ""})
    )


def get_latest_sleep_record_needing_note(queryset):
    for sleep_record in queryset.order_by("-sleep_date"):
        try:
            sleep_note = sleep_record.note
        except SleepNote.DoesNotExist:
            return sleep_record

        if is_sleep_note_effectively_empty(sleep_note):
            return sleep_record

    return queryset.order_by("-sleep_date").first()


def build_evening_plan_cards(profile, stats_7, active_hypothesis_summary, last_sleep_note):
    note_summary = (
        last_sleep_note.get_sleep_quality_display()
        if last_sleep_note is not None and last_sleep_note.sleep_quality
        else "Brak ostatniej samooceny"
    )
    experiment_label = (
        profile.get_active_hypothesis_display()
        if profile.active_hypothesis
        else "Brak aktywnego eksperymentu"
    )
    return [
        {
            "label": "Cel na noc",
            "value": f"{profile.sleep_goal_hours} h",
            "body": "To Twój aktualny punkt odniesienia przed snem.",
        },
        {
            "label": "Rytm z 7 dni",
            "value": stats_7["avg_sleep_display"],
            "body": "Szybkie przypomnienie, ile snu wychodzi Ci ostatnio średnio.",
        },
        {
            "label": "Eksperyment",
            "value": experiment_label,
            "body": active_hypothesis_summary["body"],
        },
        {
            "label": "Ostatnia samoocena",
            "value": note_summary,
            "body": "Możesz do niej wrócić, jeśli chcesz zauważyć powtarzający się wzorzec.",
        },
    ]


def build_evening_checklist(last_sleep_note):
    caffeine_hint = (
        "Ostatnio pojawiła się kofeina, więc dziś warto zakończyć ją wcześniej."
        if last_sleep_note is not None and last_sleep_note.caffeine_used
        else "Jeśli sięgasz po kofeinę, dobrze zamknąć ją odpowiednio wcześnie."
    )
    stress_hint = (
        f"Ostatni zapis stresu to {last_sleep_note.stress_level}/10, więc przyda się spokojniejsze zejście z dnia."
        if last_sleep_note is not None and last_sleep_note.stress_level is not None
        else "Dwie minuty spokojnego wyciszenia potrafią zrobić różnicę."
    )
    return [
        {
            "title": "Domknij wieczór spokojnie",
            "body": "Odłóż najmocniejsze bodźce i daj sobie chwilę na lżejszy rytm przed snem.",
        },
        {
            "title": "Pomyśl o kofeinie i ekranach",
            "body": caffeine_hint,
        },
        {
            "title": "Zaznacz, jak minął dzień",
            "body": stress_hint,
        },
    ]


def build_morning_cards(last_sleep, last_sleep_note, evaluation):
    return [
        {
            "label": "Ostatnia noc",
            "value": last_sleep.sleep_duration_display if last_sleep else "-",
            "body": "Długość snu z ostatniego zapisu.",
        },
        {
            "label": "Ocena aplikacji",
            "value": f"{evaluation['score']}%" if evaluation else "Brak",
            "body": evaluation["label"] if evaluation else "Dodaj dane, aby dostać podsumowanie nocy.",
        },
        {
            "label": "Twoja samoocena",
            "value": (
                last_sleep_note.get_sleep_quality_display()
                if last_sleep_note is not None
                else "Brak notatki"
            ),
            "body": "Krótka subiektywna ocena, do której możesz wrócić później.",
        },
        {
            "label": "Stres poprzedniego dnia",
            "value": (
                f"{last_sleep_note.stress_level}/10"
                if last_sleep_note is not None and last_sleep_note.stress_level is not None
                else "-"
            ),
            "body": "Ta liczba pomaga łapać związek między napięciem a jakością snu.",
        },
    ]


def build_habit_cards(queryset):
    today = timezone.localdate()
    note_records = queryset.filter(
        sleep_date__gte=today - timedelta(days=29)
    ).filter(build_filled_note_query())
    cards = [
        {
            "name": "Kofeina",
            "slug": "caffeine",
            "summary": analyze_boolean_hypothesis(
                note_records,
                field_name="note__caffeine_used",
                title="Wpływ kofeiny",
                factor_label="z kofeiną",
                without_label="bez kofeiny",
            ),
            "body": "Porównanie nocy z kofeiną i bez niej w ostatnich 30 dniach.",
        },
        {
            "name": "Drzemki",
            "slug": "nap",
            "summary": analyze_boolean_hypothesis(
                note_records,
                field_name="note__nap_taken",
                title="Wpływ drzemek",
                factor_label="z drzemką",
                without_label="bez drzemki",
            ),
            "body": "Czy drzemki dokładają regeneracji czy rozbijają nocny sen.",
        },
        {
            "name": "Alkohol",
            "slug": "alcohol",
            "summary": analyze_boolean_hypothesis(
                note_records,
                field_name="note__alcohol",
                title="Wpływ alkoholu",
                factor_label="z alkoholem",
                without_label="bez alkoholu",
            ),
            "body": "Sygnał, czy po alkoholu noc robi się krótsza lub mniej stabilna.",
        },
        {
            "name": "Trening",
            "slug": "training",
            "summary": analyze_boolean_hypothesis(
                note_records,
                field_name="note__training_done",
                title="Wpływ treningu",
                factor_label="po treningu",
                without_label="bez treningu",
            ),
            "body": "Zależność między aktywnością fizyczną a snem.",
        },
        {
            "name": "Stres",
            "slug": "stress",
            "summary": analyze_stress_hypothesis(note_records),
            "body": "Porównanie spokojniejszych i trudniejszych dni.",
        },
    ]
    return {
        "cards": cards,
        "notes_total": note_records.count(),
        "window_label": "ostatnie 30 dni",
    }


def build_insight_journal_entries(queryset, profile):
    self_comparison = build_self_comparison(queryset)
    insights = build_self_insights(queryset, profile, self_comparison)
    entries = [
        {
            "kind": "Automatyczny wniosek",
            "date_label": "Ostatnie 30 dni",
            "tone": insight["tone"],
            "title": insight["title"],
            "body": insight["body"],
        }
        for insight in insights
    ]

    hypothesis_summary = build_active_hypothesis_summary(queryset, profile)
    if hypothesis_summary["state"] != "inactive":
        entries.insert(
            0,
            {
                "kind": "Eksperyment miesiąca",
                "date_label": "Aktywny teraz",
                "tone": hypothesis_summary["tone"],
                "title": hypothesis_summary["title"],
                "body": hypothesis_summary["body"],
            },
        )

    recent_notes = queryset.filter(note__isnull=False).exclude(note__note_text="")[:3]
    note_entries = [
        {
            "date_label": record.sleep_date.strftime("%d.%m.%Y"),
            "text": record.note.note_text,
            "sleep_label": record.sleep_duration_display,
        }
        for record in recent_notes
    ]
    return entries, note_entries


@login_required
def evening_checkin_view(request: HttpRequest) -> HttpResponse:
    profile = request.user.profile
    sleep_records = get_user_sleep_records(request.user)
    last_sleep = sleep_records.order_by("-sleep_date").first()
    last_sleep_note = get_last_sleep_note(last_sleep)
    stats_7 = build_sleep_stats(sleep_records, 7)
    active_hypothesis_summary = build_active_hypothesis_summary(sleep_records, profile)

    context = {
        "profile": profile,
        "last_sleep": last_sleep,
        "last_sleep_note": last_sleep_note,
        "plan_cards": build_evening_plan_cards(
            profile,
            stats_7,
            active_hypothesis_summary,
            last_sleep_note,
        ),
        "checklist": build_evening_checklist(last_sleep_note),
        "stats_7": stats_7,
        "active_hypothesis_summary": active_hypothesis_summary,
    }
    return render(request, "accounts/evening_checkin.html", context)


@login_required
def morning_checkin_view(request: HttpRequest) -> HttpResponse:
    profile = request.user.profile
    sleep_records = get_user_sleep_records(request.user)
    last_sleep = sleep_records.order_by("-sleep_date").first()
    last_sleep_note = get_last_sleep_note(last_sleep)
    sleep_record_needing_note = get_latest_sleep_record_needing_note(sleep_records)
    evaluation = (
        build_sleep_auto_evaluation(last_sleep, last_sleep_note, profile)
        if last_sleep is not None
        else None
    )
    context = {
        "profile": profile,
        "last_sleep": last_sleep,
        "last_sleep_note": last_sleep_note,
        "sleep_record_needing_note": sleep_record_needing_note,
        "evaluation": evaluation,
        "morning_cards": build_morning_cards(last_sleep, last_sleep_note, evaluation),
    }
    return render(request, "accounts/morning_checkin.html", context)


@login_required
def habits_center_view(request: HttpRequest) -> HttpResponse:
    profile = request.user.profile
    sleep_records = get_user_sleep_records(request.user)
    habits = build_habit_cards(sleep_records)
    context = {
        "profile": profile,
        "habit_cards": habits["cards"],
        "habit_notes_total": habits["notes_total"],
        "habit_window_label": habits["window_label"],
        "active_hypothesis_summary": build_active_hypothesis_summary(sleep_records, profile),
    }
    return render(request, "accounts/habits_center.html", context)


@login_required
def insights_journal_view(request: HttpRequest) -> HttpResponse:
    profile = request.user.profile
    sleep_records = get_user_sleep_records(request.user)
    journal_entries, note_entries = build_insight_journal_entries(sleep_records, profile)
    context = {
        "profile": profile,
        "journal_entries": journal_entries,
        "note_entries": note_entries,
    }
    return render(request, "accounts/insights_journal.html", context)


def get_friendship_for_users(user, other_user):
    return Friendship.objects.filter(
        Q(sender=user, receiver=other_user) | Q(sender=other_user, receiver=user),
        status=Friendship.STATUS_ACCEPTED,
    ).first()


@login_required
def profile_view(request: HttpRequest, username: str | None = None) -> HttpResponse:
    if username is not None:
        profile_user = User.objects.filter(username=username).select_related("profile").first()
        if profile_user is None:
            raise Http404("Nie znaleziono użytkownika.")
        if profile_user == request.user:
            return redirect("profile")

        friendship = get_friendship_for_users(request.user, profile_user)
        if friendship is None:
            raise Http404("Ten profil nie jest dostępny.")

        sleep_records = SleepRecord.objects.filter(user=profile_user).select_related("note")
        badges = build_badges(sleep_records)

        messages.success(request, "TO JEST NOWY PROFILE VIEW")

        return render(
            request,
            "accounts/friend_profile.html",
            {
                "profile": profile_user.profile,
                "profile_user": profile_user,
                "badges": badges,
                "badges_total": len(badges),
                "sleep_records_total": sleep_records.count(),
                "friendship_since": friendship.responded_at or friendship.updated_at,
            },
        )

    profile = request.user.profile
    is_edit_mode = request.method == "POST" or request.GET.get("edit") == "1"

    user_sleep_records = SleepRecord.objects.filter(user=request.user).select_related("note")
    badges = build_badges(user_sleep_records)
    badges_total = len(badges)
    badges_earned_count = sum(1 for badge in badges if badge["earned"])
    sleep_entries_count = user_sleep_records.count()
    profile_completion = calculate_profile_completion(profile, request.user)
    sync_connections = build_sync_connections(request.user)

    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Profil został zaktualizowany.")
            return redirect("profile")
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileForm(instance=profile)

    return render(
        request,
        "accounts/profile.html",
        {
            "user_form": user_form,
            "profile_form": profile_form,
            "profile": profile,
            "is_edit_mode": is_edit_mode,
            "badges": badges[:4],
            "badges_total": badges_total,
            "badges_earned_count": badges_earned_count,
            "sleep_entries_count": sleep_entries_count,
            "profile_completion": profile_completion,
            "sync_connections": sync_connections,
        },
    )


@login_required
def sync_sources_view(request: HttpRequest) -> HttpResponse:
    profile = request.user.profile
    sync_connections = build_sync_connections(request.user)

    if request.method == "POST":
        form = SyncSourceSelectionForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Źródło danych zostało zapisane.")
            return redirect("sync_sources")
    else:
        form = SyncSourceSelectionForm(instance=profile)

    return render(
        request,
        "accounts/sync_sources.html",
        {
            "profile": profile,
            "form": form,
            "sync_connections": sync_connections,
        },
    )


def parse_bearer_token(request):
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return ""


@csrf_exempt
@require_POST
def mobile_login_api_view(request: HttpRequest) -> HttpResponse:
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({"detail": "Nieprawidłowy JSON."}, status=400)

    login_value = str(payload.get("login") or "").strip()
    password = str(payload.get("password") or "")

    if not login_value or not password:
        return JsonResponse({"detail": "Podaj login i hasło."}, status=400)

    username = login_value
    if "@" in login_value:
        matched_user = User.objects.filter(email__iexact=login_value).first()
        if matched_user:
            username = matched_user.username

    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"detail": "Niepoprawny login lub hasło."}, status=401)
    if not user.is_active:
        return JsonResponse({"detail": "Konto nie jest jeszcze aktywne."}, status=403)

    token, _ = SleepApiToken.objects.get_or_create(user=user)
    plain_token = token.rotate_key()
    token.last_used_at = timezone.now()
    token.save()

    return JsonResponse(
        {
            "status": "ok",
            "token": plain_token,
            "user": {
                "username": user.username,
                "display_name": user.profile.display_name or user.username,
                "preferred_sync_source": user.profile.preferred_sync_source,
            },
        }
    )


@csrf_exempt
@require_POST
def mobile_signup_api_view(request: HttpRequest) -> HttpResponse:
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({"detail": "Nieprawidłowy JSON."}, status=400)

    form = SignupForm(
        {
            "email": payload.get("email", ""),
            "age_group": payload.get("age_group", ""),
            "parent_email": payload.get("parent_email", ""),
            "password1": payload.get("password1", ""),
            "password2": payload.get("password2", ""),
        }
    )

    if not form.is_valid():
        return JsonResponse(
            {
                "detail": "Nie udało się założyć konta.",
                "errors": form.errors,
            },
            status=400,
        )

    user = form.save()
    if user.profile.is_child_account:
        send_parental_consent_email(request, user)
        return JsonResponse(
            {
                "status": "ok",
                "flow": "child",
                "message": "Konto dziecka utworzone. Rodzic lub opiekun musi potwierdzić zgodę przez e-mail.",
            }
        )

    send_activation_email(request, user)
    return JsonResponse(
        {
            "status": "ok",
            "flow": "adult",
            "message": "Konto utworzone. Sprawdź e-mail i aktywuj konto przed logowaniem.",
        }
    )


@require_GET
def mobile_summary_api_view(request: HttpRequest) -> HttpResponse:
    token = get_sleep_api_token(parse_bearer_token(request))
    if token is None:
        return JsonResponse({"detail": "Brak poprawnego tokenu API."}, status=401)

    user = token.user
    profile = user.profile
    last_sleep = SleepRecord.objects.filter(user=user).order_by("-sleep_date").first()
    sync_connections = build_sync_connections(user)

    token.last_used_at = timezone.now()
    token.save(update_fields=["last_used_at"])

    return JsonResponse(
        {
            "status": "ok",
            "user": {
                "username": user.username,
                "display_name": profile.display_name or user.username,
            },
            "preferred_sync_source": profile.preferred_sync_source,
            "sleep_goal_hours": profile.sleep_goal_hours,
            "last_sleep": {
                "date": last_sleep.sleep_date.isoformat() if last_sleep else None,
                "duration_display": last_sleep.sleep_duration_display if last_sleep else None,
                "source": last_sleep.source if last_sleep else None,
            },
            "sync_connections": sync_connections,
        }
    )


@csrf_exempt
@require_POST
def mobile_preferences_api_view(request: HttpRequest) -> HttpResponse:
    token = get_sleep_api_token(parse_bearer_token(request))
    if token is None:
        return JsonResponse({"detail": "Brak poprawnego tokenu API."}, status=401)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({"detail": "Nieprawidłowy JSON."}, status=400)

    preferred_sync_source = str(payload.get("preferred_sync_source") or "").strip()
    allowed_sources = {
        UserProfile.SYNC_SOURCE_HEALTH_CONNECT,
        UserProfile.SYNC_SOURCE_ZEPP_LIFE,
    }
    if preferred_sync_source not in allowed_sources:
        return JsonResponse({"detail": "Nieobsługiwane źródło danych."}, status=400)

    profile = token.user.profile
    profile.preferred_sync_source = preferred_sync_source
    profile.save(update_fields=["preferred_sync_source", "updated_at"])

    return JsonResponse(
        {
            "status": "ok",
            "preferred_sync_source": profile.preferred_sync_source,
        }
    )


def build_sync_connections(user):
    health_connection = SleepSyncConnection.objects.filter(
        user=user,
        provider=SleepRecord.SOURCE_HEALTH_CONNECT,
    ).first()
    zepp_connection = SleepSyncConnection.objects.filter(
        user=user,
        provider=SleepRecord.SOURCE_ZEPP_SYNC,
    ).first()
    latest_zepp_import = ImportHistory.objects.filter(
        user=user,
        source=SleepRecord.SOURCE_ZEPP_LIFE,
    ).first()
    connections = [
        {
            "provider": SleepRecord.SOURCE_HEALTH_CONNECT,
            "label": "Health Connect",
            "badge": "Automatyczne",
            "description": "Najlepsza opcja dla Androida. Aplikacja mobilna pobiera dane snu z Health Connect i wysyła je do SleepWatch po każdej synchronizacji telefonu.",
            "is_connected": bool(health_connection and health_connection.last_synced_at),
            "status_label": "Połączono" if health_connection and health_connection.last_synced_at else "Gotowe do podłączenia",
            "last_synced_at": health_connection.last_synced_at if health_connection else None,
            "last_imported_count": health_connection.last_imported_count if health_connection else 0,
            "last_error": health_connection.last_error if health_connection else "",
            "last_device_name": health_connection.last_device_name if health_connection else "",
            "next_step": "Wybierz to źródło, jeśli Twoje urządzenie zapisuje sen w Health Connect.",
            "is_recommended": True,
            "supports_realtime": True,
            "sync_mode_label": "Automatycznie po synchronizacji telefonu",
            "action_label": "",
            "action_url": "",
        },
        {
            "provider": SleepRecord.SOURCE_ZEPP_LIFE,
            "label": "Zepp Life",
            "badge": "Automatyczne / CSV",
            "description": "Dla opasek Amazfit i Mi Band. Dane mogą trafić do SleepWatch przez aplikację mobilną albo przez import pliku CSV.",
            "is_connected": bool(
                (zepp_connection and zepp_connection.last_synced_at)
                or latest_zepp_import
            ),
            "status_label": "Dane z Zepp wykryte" if latest_zepp_import else "Do przygotowania",
            "last_synced_at": (
                (zepp_connection.last_synced_at if zepp_connection and zepp_connection.last_synced_at else None)
                or (latest_zepp_import.imported_at if latest_zepp_import else None)
            ),
            "last_imported_count": (
                zepp_connection.last_imported_count
                if zepp_connection and zepp_connection.last_imported_count
                else (latest_zepp_import.added_count if latest_zepp_import else 0)
            ),
            "last_error": zepp_connection.last_error if zepp_connection else "",
            "last_device_name": zepp_connection.last_device_name if zepp_connection else "Zepp Life",
            "next_step": "Jeśli używasz aplikacji mobilnej SleepWatch, wybierz Zepp Life jako źródło. Jeśli nie, wgraj plik CSV ręcznie.",
            "is_recommended": False,
            "supports_realtime": True,
            "sync_mode_label": "Aplikacja mobilna albo import CSV",
            "action_label": "Importuj dane Zepp",
            "action_url": reverse("sleep_import"),
        },
    ]

    return connections


def build_friends_context(user, query=""):
    accepted_friendships = Friendship.objects.filter(
        Q(sender=user) | Q(receiver=user),
        status=Friendship.STATUS_ACCEPTED,
    ).select_related("sender__profile", "receiver__profile")
    incoming_requests = Friendship.objects.filter(
        receiver=user,
        status=Friendship.STATUS_PENDING,
    ).select_related("sender__profile")
    outgoing_requests = Friendship.objects.filter(
        sender=user,
        status=Friendship.STATUS_PENDING,
    ).select_related("receiver__profile")

    friends = []
    friend_ids = set()
    for friendship in accepted_friendships:
        friend = friendship.receiver if friendship.sender_id == user.id else friendship.sender
        friend_ids.add(friend.id)
        friends.append(
            {
                "id": friendship.id,
                "user_id": friend.id,
                "username": friend.username,
                "display_name": friend.profile.display_name or friend.username,
                "avatar": friend.profile.avatar,
                "avatar_symbol": friend.profile.avatar_symbol,
                "status_since": friendship.responded_at or friendship.updated_at,
            }
        )

    related_user_ids = set(friend_ids)
    related_user_ids.add(user.id)
    related_user_ids.update(outgoing_requests.values_list("receiver_id", flat=True))
    related_user_ids.update(incoming_requests.values_list("sender_id", flat=True))

    search_results = []
    normalized_query = (query or "").strip()
    if normalized_query:
        users = (
            User.objects.filter(
                Q(username__icontains=normalized_query)
                | Q(email__icontains=normalized_query)
                | Q(profile__display_name__icontains=normalized_query)
            )
            .exclude(id__in=related_user_ids)
            .select_related("profile")
            .order_by("username")[:8]
        )
        search_results = [
            {
                "user_id": candidate.id,
                "username": candidate.username,
                "display_name": candidate.profile.display_name or candidate.username,
                "avatar": candidate.profile.avatar,
                "avatar_symbol": candidate.profile.avatar_symbol,
                "meta": candidate.email,
            }
            for candidate in users
        ]

    incoming_request_cards = [
        {
            "id": friendship.id,
            "user_id": friendship.sender.id,
            "username": friendship.sender.username,
            "display_name": friendship.sender.profile.display_name or friendship.sender.username,
            "avatar": friendship.sender.profile.avatar,
            "avatar_symbol": friendship.sender.profile.avatar_symbol,
            "created_at": friendship.created_at,
        }
        for friendship in incoming_requests
    ]
    outgoing_request_cards = [
        {
            "id": friendship.id,
            "user_id": friendship.receiver.id,
            "username": friendship.receiver.username,
            "display_name": friendship.receiver.profile.display_name or friendship.receiver.username,
            "avatar": friendship.receiver.profile.avatar,
            "avatar_symbol": friendship.receiver.profile.avatar_symbol,
            "created_at": friendship.created_at,
        }
        for friendship in outgoing_requests
    ]
    friends.sort(key=lambda item: item["display_name"].lower())

    return {
        "friends": friends,
        "friends_count": len(friends),
        "incoming_requests": incoming_request_cards,
        "outgoing_requests": outgoing_request_cards,
        "pending_total": len(incoming_request_cards) + len(outgoing_request_cards),
        "search_query": normalized_query,
        "search_results": search_results,
    }


@login_required
def friends_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        action = request.POST.get("action", "").strip()
        target_user_id = request.POST.get("user_id", "").strip()
        friendship_id = request.POST.get("friendship_id", "").strip()

        if action == "send_request":
            if not target_user_id.isdigit():
                messages.error(request, "Nie udało się wysłać zaproszenia.")
                return redirect("friends")

            if int(target_user_id) == request.user.id:
                messages.error(request, "Nie można dodać samej siebie do znajomych.")
                return redirect("friends")

            target_user = User.objects.filter(pk=target_user_id).first()
            if target_user is None:
                messages.error(request, "Nie znaleziono tego użytkownika.")
                return redirect("friends")

            existing = Friendship.objects.filter(
                Q(sender=request.user, receiver=target_user)
                | Q(sender=target_user, receiver=request.user)
            ).first()
            if existing:
                if existing.status == Friendship.STATUS_ACCEPTED:
                    messages.info(request, "Ta osoba jest już w Twoich znajomych.")
                elif existing.status == Friendship.STATUS_PENDING:
                    messages.info(request, "Zaproszenie jest już w toku.")
                else:
                    existing.sender = request.user
                    existing.receiver = target_user
                    existing.status = Friendship.STATUS_PENDING
                    existing.responded_at = None
                    existing.save(update_fields=["sender", "receiver", "status", "responded_at", "updated_at"])
                    messages.success(request, "Wysłałyśmy nowe zaproszenie do znajomych.")
                return redirect("friends")

            Friendship.objects.create(
                sender=request.user,
                receiver=target_user,
                status=Friendship.STATUS_PENDING,
            )
            messages.success(request, "Zaproszenie do znajomych zostało wysłane.")
            return redirect("friends")

        if not friendship_id.isdigit():
            messages.error(request, "Nie znaleziono tej relacji.")
            return redirect("friends")

        friendship = Friendship.objects.filter(pk=friendship_id).select_related("sender", "receiver").first()
        if friendship is None:
            messages.error(request, "Nie znaleziono tej relacji.")
            return redirect("friends")

        if action == "accept_request" and friendship.receiver_id == request.user.id:
            friendship.status = Friendship.STATUS_ACCEPTED
            friendship.responded_at = timezone.now()
            friendship.save(update_fields=["status", "responded_at", "updated_at"])
            messages.success(request, "Zaproszenie zostało zaakceptowane.")
            return redirect("friends")

        if action == "decline_request" and friendship.receiver_id == request.user.id:
            friendship.status = Friendship.STATUS_DECLINED
            friendship.responded_at = timezone.now()
            friendship.save(update_fields=["status", "responded_at", "updated_at"])
            messages.success(request, "Zaproszenie zostało odrzucone.")
            return redirect("friends")

        if action == "cancel_request" and friendship.sender_id == request.user.id:
            friendship.delete()
            messages.success(request, "Zaproszenie zostało anulowane.")
            return redirect("friends")

        if (
            action == "remove_friend"
            and friendship.status == Friendship.STATUS_ACCEPTED
            and request.user.id in {friendship.sender_id, friendship.receiver_id}
        ):
            friendship.delete()
            messages.success(request, "Znajomy został usunięty z listy.")
            return redirect("friends")

        messages.error(request, "Ta akcja nie jest dostępna.")
        return redirect("friends")

    context = {
        "profile": request.user.profile,
        **build_friends_context(request.user, request.GET.get("q", "")),
    }
    return render(request, "accounts/friends.html", context)


@login_required
def achievements_view(request: HttpRequest) -> HttpResponse:
    profile = request.user.profile
    badges = build_badges(SleepRecord.objects.filter(user=request.user).select_related("note"))
    earned_badges = sum(1 for badge in badges if badge["earned"])
    badges_total = len(badges)
    return render(
        request,
        "accounts/achievements.html",
        {
            "profile": profile,
            "badges": badges,
            "earned_badges": earned_badges,
            "badges_total": badges_total,
            "badges_progress": round((earned_badges / badges_total) * 100) if badges_total else 0,
        },
    )


@login_required
def peer_sleep_view(request: HttpRequest) -> HttpResponse:
    profile = request.user.profile
    context = {
        "profile": profile,
        "peer_comparison": build_peer_comparison(request.user, profile),
    }
    return render(request, "accounts/peer_sleep.html", context)


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


def send_parental_consent_email(request: HttpRequest, user: User) -> None:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = parental_consent_token.make_token(user)
    consent_link = request.build_absolute_uri(
        reverse_lazy("activate_child_account", kwargs={"uidb64": uid, "token": token})
    )
    message = render_to_string(
        "accounts/emails/parental_consent_email.txt",
        {
            "user": user,
            "consent_link": consent_link,
        },
    )
    send_mail(
        subject="SleepWatch - zgoda rodzica lub opiekuna",
        message=message,
        from_email=None,
        recipient_list=[user.profile.parent_email],
    )


def calculate_profile_completion(profile, user=None) -> int:
    fields = [
        bool(getattr(profile, "display_name", "")),
        bool(getattr(user, "email", "") if user else False),
        bool(getattr(profile, "avatar", "")),
        bool(getattr(profile, "age_group", "")),
        bool(getattr(profile, "lifestyle", "")),
        bool(getattr(profile, "sleep_goal_hours", None)),
    ]
    return int((sum(fields) / len(fields)) * 100)


def build_dashboard_tip(last_sleep_evaluation, profile_completion, stats_7):
    if profile_completion < 100:
        return {
            "title": "Dopełnij profil",
            "body": "Uzupełnij brakujące informacje, aby aplikacja lepiej dopasowywała wskazówki.",
            "tone": "neutral",
        }

    if stats_7["total"] < 3:
        return {
            "title": "Dodawaj kolejne noce",
            "body": "Po kilku kolejnych zapisach dashboard pokaże bardziej konkretne trendy i porównania.",
            "tone": "neutral",
        }

    if last_sleep_evaluation and last_sleep_evaluation["score"] >= 80:
        return {
            "title": "Dobry kierunek",
            "body": "Ostatnia noc wyglądała dobrze. Spróbuj utrzymać podobną regularność jeszcze przez kilka dni.",
            "tone": "positive",
        }

    return {
        "title": "Mała wskazówka na dziś",
        "body": "Jeśli możesz, postaw dziś na spokojniejszy wieczór i regularną godzinę zaśnięcia.",
        "tone": "warning",
    }


def build_peer_comparison(user, profile):
    if not profile.age_group or not profile.lifestyle:
        return {
            "is_available": False,
            "title": "Sen w Twojej grupie",
            "body": "Uzupełnij grupę wiekową i aktywność fizyczną, aby porównać swój sen z podobnymi osobami.",
        }

    start_date = timezone.localdate() - timedelta(days=29)
    peer_records = (
        SleepRecord.objects.filter(
            sleep_date__gte=start_date,
            user__profile__age_group=profile.age_group,
            user__profile__lifestyle=profile.lifestyle,
        )
        .exclude(user=user)
        .select_related("user", "note")
    )
    peer_users_count = (
        UserProfile.objects.filter(age_group=profile.age_group, lifestyle=profile.lifestyle)
        .exclude(user=user)
        .count()
    )

    if not peer_records.exists():
        return {
            "is_available": False,
            "title": "Sen w Twojej grupie",
            "body": "Na razie brakuje danych innych osób z tej samej grupy wiekowej i aktywności.",
        }

    your_records = SleepRecord.objects.filter(user=user, sleep_date__gte=start_date).select_related("note")
    your_aggregates = your_records.aggregate(
        avg_sleep=Avg("sleep_duration_minutes"),
        avg_awakenings=Avg("awakenings_count"),
    )
    peer_aggregates = peer_records.aggregate(
        avg_sleep=Avg("sleep_duration_minutes"),
        avg_awakenings=Avg("awakenings_count"),
    )

    your_good_share = build_good_night_share(your_records)
    peer_good_share = build_good_night_share(peer_records)

    your_avg_sleep = round(your_aggregates["avg_sleep"] or 0, 1)
    peer_avg_sleep = round(peer_aggregates["avg_sleep"] or 0, 1)
    your_avg_awakenings = round(your_aggregates["avg_awakenings"], 1) if your_aggregates["avg_awakenings"] is not None else None
    peer_avg_awakenings = round(peer_aggregates["avg_awakenings"], 1) if peer_aggregates["avg_awakenings"] is not None else None

    peer_members = build_peer_members(peer_records)

    return {
        "is_available": True,
        "peer_users_count": peer_users_count,
        "peer_members": peer_members,
        "sleep": {
            "you": minutes_to_display(your_avg_sleep) if your_avg_sleep else "-",
            "group": minutes_to_display(peer_avg_sleep) if peer_avg_sleep else "-",
            "delta": format_minutes_delta(round(your_avg_sleep - peer_avg_sleep, 1)) if your_avg_sleep and peer_avg_sleep else "-",
        },
        "awakenings": {
            "you": format_decimal(your_avg_awakenings),
            "group": format_decimal(peer_avg_awakenings),
            "delta": format_decimal_delta(your_avg_awakenings, peer_avg_awakenings),
        },
        "good_nights": {
            "you": f"{your_good_share}%" if your_good_share is not None else "-",
            "group": f"{peer_good_share}%" if peer_good_share is not None else "-",
            "delta": format_percentage_point_delta(your_good_share, peer_good_share),
        },
    }


def build_peer_members(records):
    grouped_records = {}

    for record in records:
        grouped_records.setdefault(record.user_id, []).append(record)

    members = []
    for user_records in grouped_records.values():
        if not user_records:
            continue

        peer_user = user_records[0].user
        peer_profile = peer_user.profile
        avg_sleep = sum(record.sleep_duration_minutes for record in user_records) / len(user_records)
        awakenings_values = [record.awakenings_count for record in user_records if record.awakenings_count is not None]
        avg_awakenings = (
            round(sum(awakenings_values) / len(awakenings_values), 1)
            if awakenings_values
            else None
        )
        latest_record = max(user_records, key=lambda item: item.sleep_date)
        good_share = build_good_night_share(user_records)

        members.append(
            {
                "name": peer_profile.display_name or peer_user.username,
                "username": peer_user.username,
                "avatar": peer_profile.avatar,
                "avatar_symbol": peer_profile.avatar_symbol,
                "avg_sleep": minutes_to_display(avg_sleep),
                "latest_sleep": latest_record.sleep_duration_display,
                "latest_date": latest_record.sleep_date.strftime("%d.%m.%Y"),
                "avg_awakenings": format_decimal(avg_awakenings),
                "good_share": f"{good_share}%" if good_share is not None else "-",
                "entries": len(user_records),
            }
        )

    members.sort(key=lambda item: item["entries"], reverse=True)
    return members


def build_good_night_share(records):
    records = list(records)
    total = len(records)
    if not total:
        return None
    counts = summarize_auto_nights(records)
    return round((counts["good_nights"] / total) * 100, 1)


def build_sleep_streak(queryset):
    dates = list(
        queryset.order_by("-sleep_date")
        .values_list("sleep_date", flat=True)
        .distinct()
    )
    if not dates:
        return {
            "count": 0,
            "label": "Brak serii",
            "body": "Dodaj pierwszą noc, aby rozpocząć swoją serię snu.",
        }

    streak = 1
    previous_date = dates[0]
    for current_date in dates[1:]:
        if previous_date - current_date == timedelta(days=1):
            streak += 1
            previous_date = current_date
            continue
        break

    return {
        "count": streak,
        "label": f"{streak} {'noc' if streak == 1 else 'noce' if 2 <= streak <= 4 else 'nocy'} z rzędu",
        "body": "Tyle kolejnych nocy masz zapisanych bez przerwy.",
    }


def build_weekly_goal(queryset):
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    weekly_records = queryset.filter(sleep_date__gte=week_start)
    target = 4
    progress = weekly_records.count()
    remaining = max(target - progress, 0)
    return {
        "target": target,
        "progress": min(progress, target),
        "completed": progress >= target,
        "label": f"{progress}/{target} nocy",
        "body": "Cel tygodnia: zapisz co najmniej 4 noce.",
        "hint": "Cel osiągnięty." if progress >= target else f"Zostało jeszcze {remaining} do celu.",
        "percent": min(int((progress / target) * 100), 100),
    }


def build_active_hypothesis_summary(queryset, profile):
    if not profile.active_hypothesis:
        return {
            "state": "inactive",
            "tone": "neutral",
            "title": "Wybierz swój eksperyment na ten miesiąc",
            "body": "Nadaj sobie mały cel na najbliższe tygodnie. SleepWatch będzie zbierał tropy i pokaże, czy dany czynnik może mieć związek z Twoim snem.",
            "meta": "Najlepiej działa to wtedy, gdy regularnie dopisujesz krótkie notatki do nocy.",
        }

    note_records = queryset.filter(
        sleep_date__gte=timezone.localdate() - timedelta(days=29)
    ).filter(build_filled_note_query())
    analyzers = {
        UserProfile.HYPOTHESIS_CAFFEINE: lambda records: analyze_boolean_hypothesis(
            records,
            field_name="note__caffeine_used",
            title="Wpływ kofeiny",
            factor_label="z kofeiną",
            without_label="bez kofeiny",
        ),
        UserProfile.HYPOTHESIS_NAP: lambda records: analyze_boolean_hypothesis(
            records,
            field_name="note__nap_taken",
            title="Wpływ drzemek",
            factor_label="z drzemką",
            without_label="bez drzemki",
        ),
        UserProfile.HYPOTHESIS_ALCOHOL: lambda records: analyze_boolean_hypothesis(
            records,
            field_name="note__alcohol",
            title="Wpływ alkoholu",
            factor_label="z alkoholem",
            without_label="bez alkoholu",
        ),
        UserProfile.HYPOTHESIS_TRAINING: lambda records: analyze_boolean_hypothesis(
            records,
            field_name="note__training_done",
            title="Wpływ treningu",
            factor_label="po treningu",
            without_label="bez treningu",
        ),
        UserProfile.HYPOTHESIS_STRESS: analyze_stress_hypothesis,
    }
    summary = analyzers.get(profile.active_hypothesis, lambda records: None)(note_records)
    if summary is None:
        return {
            "state": "inactive",
            "tone": "neutral",
            "title": "Wybierz swój eksperyment na ten miesiąc",
            "body": "Nadaj sobie mały cel na najbliższe tygodnie. SleepWatch będzie zbierał tropy i pokaże, czy dany czynnik może mieć związek z Twoim snem.",
            "meta": "Najlepiej działa to wtedy, gdy regularnie dopisujesz krótkie notatki do nocy.",
        }

    summary["started_at"] = profile.active_hypothesis_started_at
    summary["hypothesis_label"] = profile.get_active_hypothesis_display()
    return summary


def analyze_boolean_hypothesis(queryset, field_name, title, factor_label, without_label):
    with_factor = queryset.filter(**{field_name: True})
    without_factor = queryset.filter(**{field_name: False})
    with_count = with_factor.count()
    without_count = without_factor.count()

    if with_count + without_count < 4:
        return {
            "state": "not_enough_notes",
            "tone": "neutral",
            "title": title,
            "body": "Uzupełnij więcej notatek. Na razie jest za mało danych, żeby pokazać sensowną analizę.",
            "meta": "Wróć tu po kilku kolejnych nocach.",
        }

    if with_count < 2 or without_count < 2:
        return {
            "state": "insufficient_split",
            "tone": "neutral",
            "title": title,
            "body": "Za mało zróżnicowanych danych do analizy. Uzupełnij kolejne notatki, żebyśmy mogli porównać ten nawyk.",
            "meta": "Najlepiej, gdy w notatkach pojawiają się różne sytuacje, a nie tylko jeden wariant.",
        }

    avg_with = with_factor.aggregate(avg=Avg("sleep_duration_minutes"))["avg"] or 0
    avg_without = without_factor.aggregate(avg=Avg("sleep_duration_minutes"))["avg"] or 0
    delta = round(avg_without - avg_with, 1)

    if abs(delta) < 20:
        return {
            "state": "no_pattern",
            "tone": "neutral",
            "title": title,
            "body": f"Na razie nie widać mocnego sygnału między nocami {factor_label} i {without_label}.",
            "meta": f"Różnica średniego czasu snu to obecnie {minutes_delta_text(abs(delta))}.",
        }

    if delta > 0:
        return {
            "state": "pattern_detected",
            "tone": "warning",
            "title": title,
            "body": f"Zaczyna być widać wzorzec: noce {factor_label} są średnio krótsze o {minutes_delta_text(delta)} niż noce {without_label}.",
            "meta": f"Porównanie opiera się na {with_count} nocach {factor_label} i {without_count} nocach {without_label}.",
        }

    return {
        "state": "pattern_detected",
        "tone": "positive",
        "title": title,
        "body": f"Na ten moment wygląda to obiecująco: noce {factor_label} są średnio dłuższe o {minutes_delta_text(abs(delta))} niż noce {without_label}.",
        "meta": f"Porównanie opiera się na {with_count} nocach {factor_label} i {without_count} nocach {without_label}.",
    }


def analyze_stress_hypothesis(queryset):
    high_stress = queryset.filter(note__stress_level__gte=7)
    low_stress = queryset.filter(note__stress_level__lte=4)
    high_count = high_stress.count()
    low_count = low_stress.count()

    if high_count + low_count < 4:
        return {
            "state": "not_enough_notes",
            "tone": "neutral",
            "title": "Wpływ stresu",
            "body": "Uzupełnij więcej ocen stresu. Na razie jest za mało danych, żeby pokazać sensowną analizę.",
            "meta": "Wróć tu po kilku kolejnych nocach.",
        }

    if high_count < 2 or low_count < 2:
        return {
            "state": "insufficient_split",
            "tone": "neutral",
            "title": "Wpływ stresu",
            "body": "Za mało zróżnicowanych danych do analizy. Uzupełnij kolejne notatki, żebyśmy mogli porównać wpływ stresu.",
            "meta": "Najlepiej, gdy w ocenach pojawiają się zarówno spokojniejsze, jak i trudniejsze dni.",
        }

    avg_high = high_stress.aggregate(avg=Avg("sleep_duration_minutes"))["avg"] or 0
    avg_low = low_stress.aggregate(avg=Avg("sleep_duration_minutes"))["avg"] or 0
    delta = round(avg_low - avg_high, 1)

    if abs(delta) < 20:
        return {
            "state": "no_pattern",
            "tone": "neutral",
            "title": "Wpływ stresu",
            "body": "Na razie nie widać mocnego wzorca między stresem a czasem snu.",
            "meta": f"Różnica średniego czasu snu to obecnie {minutes_delta_text(abs(delta))}.",
        }

    if delta > 0:
        return {
            "state": "pattern_detected",
            "tone": "warning",
            "title": "Wpływ stresu",
            "body": f"Zaczyna być widać, że noce po dniach z wyższym stresem są średnio krótsze o {minutes_delta_text(delta)}.",
            "meta": f"Porównanie opiera się na {high_count} nocach z wysokim stresem i {low_count} nocach z niskim stresem.",
        }

    return {
        "state": "pattern_detected",
        "tone": "positive",
        "title": "Wpływ stresu",
        "body": f"Na ten moment wyższy stres nie wygląda na czynnik skracający sen. Różnica to {minutes_delta_text(abs(delta))}.",
        "meta": f"Porównanie opiera się na {high_count} nocach z wysokim stresem i {low_count} nocach z niskim stresem.",
    }


def build_dashboard_alerts(queryset, profile, profile_completion, weekly_goal):
    alerts = []

    if profile_completion < 100:
        alerts.append(
            {
                "tone": "warning",
                "title": "Dokończ profil i odblokuj trafniejsze wskazówki",
                "body": "Uzupełnij grupę wiekową, aktywność i cel snu, żeby aplikacja lepiej dopasowywała podpowiedzi do Ciebie.",
            }
        )

    if not weekly_goal["completed"]:
        alerts.append(
            {
                "tone": "neutral",
                "title": "Cel tygodnia: zapisuj noce regularnie",
                "body": f"Masz obecnie {weekly_goal['label']}. {weekly_goal['hint']}",
            }
        )

    hypothesis_summary = build_active_hypothesis_summary(queryset, profile)
    if hypothesis_summary["state"] == "inactive":
        alerts.append(
            {
                "tone": "neutral",
                "title": "Wybierz eksperyment miesiąca",
                "body": "Nadaj sobie prosty kierunek: sprawdź, czy kofeina, stres, drzemki, alkohol albo trening mają związek z Twoim snem.",
            }
        )
    elif hypothesis_summary["state"] == "pattern_detected":
        alerts.append(
            {
                "tone": hypothesis_summary["tone"],
                "title": f"Hipoteza: {hypothesis_summary['title']}",
                "body": hypothesis_summary["body"],
            }
        )
    else:
        alerts.append(
            {
                "tone": "neutral",
                "title": f"Hipoteza: {hypothesis_summary['title']}",
                "body": hypothesis_summary["body"],
            }
        )

    if not queryset.exists():
        alerts.insert(
            0,
            {
                "tone": "neutral",
                "title": "Dodaj pierwsze noce i uruchom swój rytm",
                "body": "Zaimportuj lub wpisz pierwsze noce, a dashboard zacznie pokazywać postęp, alerty i wyniki eksperymentów.",
            },
        )

    return alerts[:3]


def build_badges(queryset):
    total_records = queryset.count()
    note_count = queryset.filter(build_filled_note_query()).count()

    streak = build_sleep_streak(queryset)["count"]
    good_nights = summarize_auto_nights(queryset)["good_nights"] if total_records else 0
    user = queryset.first().user if total_records else None
    profile = getattr(user, "profile", None) if user else None

    profile_complete = bool(
        profile
        and profile.display_name
        and user
        and user.email
        and profile.avatar
        and profile.age_group
        and profile.lifestyle
        and profile.sleep_goal_hours
    )

    badges = [
        {
            "icon": "✦",
            "title": "Pierwszy krok",
            "description": "Dodaj pierwszą noc do swojej historii.",
            "earned": total_records >= 1,
        },
        {
            "icon": "✎",
            "title": "Uważna obserwacja",
            "description": "Dodaj notatki do co najmniej 3 nocy.",
            "earned": note_count >= 3,
        },
        {
            "icon": "☾",
            "title": "Mocna seria",
            "description": "Zapisuj sen przez 5 nocy z rzędu.",
            "earned": streak >= 5,
        },
        {
            "icon": "★",
            "title": "Dobre noce",
            "description": "Zbierz 3 dobre noce według oceny aplikacji.",
            "earned": good_nights >= 3,
        },
        {
            "icon": "✓",
            "title": "Pełny profil",
            "description": "Uzupełnij nazwę, e-mail, grupę wiekową, aktywność i cel snu.",
            "earned": profile_complete,
        },
        {
            "icon": "◔",
            "title": "10 nocy",
            "description": "Zapisz co najmniej 10 nocy w swojej historii.",
            "earned": total_records >= 10,
        },
        {
            "icon": "◕",
            "title": "30 nocy",
            "description": "Zbuduj dłuższą historię i zapisz 30 nocy.",
            "earned": total_records >= 30,
        },
        {
            "icon": "✍",
            "title": "Notatkowy rytm",
            "description": "Dodaj notatki do co najmniej 7 nocy.",
            "earned": note_count >= 7,
        },
    ]
    return badges


def build_sleep_stats(queryset, days):
    start_date = timezone.localdate() - timedelta(days=days - 1)
    records = queryset.filter(sleep_date__gte=start_date)
    total = records.count()
    aggregates = records.aggregate(
        avg_sleep=Avg("sleep_duration_minutes"),
        avg_hr=Avg("avg_heart_rate"),
        avg_spo2=Avg("min_spo2"),
    )
    auto_counts = summarize_auto_nights(records)
    avg_sleep = aggregates["avg_sleep"] or 0
    hours = int(avg_sleep // 60) if avg_sleep else 0
    minutes = int(avg_sleep % 60) if avg_sleep else 0
    return {
        "days": days,
        "total": total,
        "avg_sleep_minutes": round(avg_sleep, 1) if total else 0,
        "avg_sleep_display": f"{hours}h {minutes:02d}m" if total else "-",
        "avg_hr": round(aggregates["avg_hr"], 1) if aggregates["avg_hr"] is not None else "-",
        "avg_spo2": round(aggregates["avg_spo2"], 1) if aggregates["avg_spo2"] is not None else "-",
        "good_nights": auto_counts["good_nights"],
        "bad_nights": auto_counts["bad_nights"],
    }


def build_chart_series(queryset, days, field_name):
    end_date = timezone.localdate()
    start_date = end_date - timedelta(days=days - 1)
    records = list(
        queryset.filter(sleep_date__range=(start_date, end_date))
        .order_by("sleep_date")
        .values_list("sleep_date", field_name)
    )
    if not records:
        return None

    labels = []
    values = []
    display_values = []

    for record_date, value in records:
        labels.append(record_date.strftime("%d.%m"))
        values.append(value)

        if value is None:
            display_values.append("-")
            continue

        if field_name == "sleep_duration_minutes":
            display_values.append(minutes_to_display(value))
        elif isinstance(value, float):
            display_values.append(str(round(value, 1)).replace(".", ","))
        else:
            display_values.append(str(value))

    numeric_values = [value for value in values if value is not None]
    if not numeric_values:
        return None

    min_numeric = min(numeric_values)
    max_numeric = max(numeric_values)

    return {
        "labels": labels,
        "values": values,
        "display_values": display_values,
        "min_value": minutes_to_display(min_numeric) if field_name == "sleep_duration_minutes" else format_decimal(min_numeric),
        "max_value": minutes_to_display(max_numeric) if field_name == "sleep_duration_minutes" else format_decimal(max_numeric),
        "total_points": len(numeric_values),
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

    actual_min_value = min(values)
    actual_max_value = max(values)
    actual_span = max(actual_max_value - actual_min_value, 1)
    padding_value = max(round(actual_span * 0.2, 1), 1)
    min_value = actual_min_value - padding_value
    max_value = actual_max_value + padding_value
    span = max(max_value - min_value, 1)

    width = 360
    height = 190
    padding_left = 34
    padding_right = 20
    padding_top = 20
    padding_bottom = 42
    chart_width = width - padding_left - padding_right
    chart_height = height - padding_top - padding_bottom
    step = chart_width / max(len(records) - 1, 1)

    points = []
    area_points = []
    labels = []
    x_ticks = []
    tick_indexes = set()

    if records:
        tick_indexes.add(0)
        tick_indexes.add(len(records) - 1)
        if len(records) > 2:
            tick_indexes.add(len(records) // 2)

    for index, (record_date, value) in enumerate(records):
        x = padding_left + index * step
        y = height - padding_bottom

        if value is not None:
            y = height - padding_bottom - ((value - min_value) / span) * chart_height
            points.append(f"{x:.2f},{y:.2f}")
            area_points.append(f"{x:.2f},{y:.2f}")
            labels.append(
                {
                    "x": round(x, 2),
                    "y": round(y, 2),
                    "value": round(value, 1) if isinstance(value, float) else value,
                    "date": record_date.strftime("%d.%m"),
                }
            )

        if index in tick_indexes:
            x_ticks.append({"label": record_date.strftime("%d.%m")})

    if not points:
        return None

    baseline_y = height - padding_bottom
    area_path = (
        f"M {padding_left:.2f},{baseline_y:.2f} "
        + " L ".join(area_points)
        + f" L {padding_left + (len(records) - 1) * step:.2f},{baseline_y:.2f} Z"
    )

    guide_values = [
        round(max_value, 1),
        round(min_value + span / 2, 1),
        round(min_value, 1),
    ]
    guides = []
    for guide_value in guide_values:
        y = height - padding_bottom - ((guide_value - min_value) / span) * chart_height
        guides.append(
            {
                "y": round(y, 2),
                "value": guide_value,
            }
        )

    return {
        "points": " ".join(points),
        "area_path": area_path,
        "labels": labels,
        "x_ticks": x_ticks,
        "guides": guides,
        "min_value": round(min_value, 1),
        "max_value": round(max_value, 1),
        "field_name": field_name,
        "width": width,
        "height": height,
        "padding_left": padding_left,
        "padding_right": padding_right,
        "padding_bottom": padding_bottom,
        "chart_end_x": width - padding_right,
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

    note_records = records_30.filter(build_filled_note_query())
    caffeine_insight = build_boolean_factor_insight(
        note_records,
        "note__caffeine_used",
        "Kofeina może skracać sen",
        "Noce po kofeinie są średnio krótsze o {delta}.",
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
    )
    auto_counts = summarize_auto_nights(records)
    avg_sleep_minutes = round(aggregates["avg_sleep"] or 0, 1)
    return {
        "total": total,
        "avg_sleep_minutes": avg_sleep_minutes,
        "avg_sleep_display": minutes_to_display(avg_sleep_minutes) if total else "-",
        "avg_hr": round(aggregates["avg_hr"], 1) if aggregates["avg_hr"] is not None else 0,
        "avg_hr_display": round(aggregates["avg_hr"], 1) if aggregates["avg_hr"] is not None else "-",
        "good_nights": auto_counts["good_nights"],
    }


def summarize_auto_nights(records):
    good_nights = 0
    bad_nights = 0

    for record in records:
        try:
            note = record.note
        except SleepNote.DoesNotExist:
            note = None

        evaluation = build_sleep_auto_evaluation(record, note, record.user.profile)
        if evaluation["label"] == "Dobra noc":
            good_nights += 1
        elif evaluation["label"] == "Słaba noc":
            bad_nights += 1

    return {
        "good_nights": good_nights,
        "bad_nights": bad_nights,
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


def format_decimal(value):
    if value is None:
        return "-"
    rounded = round(value, 1)
    if float(rounded).is_integer():
        return str(int(rounded))
    return str(rounded).replace(".", ",")


def format_decimal_delta(current, previous):
    if current is None or previous is None:
        return "-"
    delta = round(current - previous, 1)
    if delta == 0:
        return "0"
    prefix = "+" if delta > 0 else ""
    return f"{prefix}{format_decimal(delta)}"


def format_percentage_point_delta(current, previous):
    if current is None or previous is None:
        return "-"
    delta = round(current - previous, 1)
    if delta == 0:
        return "0 pp"
    prefix = "+" if delta > 0 else ""
    return f"{prefix}{str(delta).replace('.', ',')} pp"

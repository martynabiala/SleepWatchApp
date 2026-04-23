import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import (
    ManualSleepRecordForm,
    SleepImportForm,
    SleepImportMappingForm,
    SleepNoteForm,
)
from .models import ImportHistory, SleepNote, SleepRecord
from .services import (
    UnrecognizedSleepCsvFormatError,
    build_sleep_auto_evaluation,
    decode_sleep_csv,
    get_sleep_api_token,
    mark_sync_error,
    parse_sleep_csv,
    parse_sleep_csv_content,
    sync_sleep_records,
)

IMPORT_MAPPING_SESSION_KEY = "sleep_import_mapping_payload"


def format_minutes_short(value):
    hours = value // 60
    minutes = value % 60
    return f"{hours}h {minutes:02d}m"


def finalize_sleep_import(request, import_result, file_name):
    rows = import_result["rows"]
    parse_errors = import_result["parse_errors"]
    detected_source = import_result["source"]
    detected_label = import_result["source_label"]
    added_count = 0
    duplicate_count = 0

    for row in rows:
        if SleepRecord.objects.filter(
            user=request.user,
            sleep_date=row["sleep_date"],
        ).exists():
            duplicate_count += 1
            continue

        try:
            with transaction.atomic():
                SleepRecord.objects.create(
                    user=request.user,
                    source=detected_source,
                    **row,
                )
            added_count += 1
        except IntegrityError:
            duplicate_count += 1

    ImportHistory.objects.create(
        user=request.user,
        source=detected_source,
        file_name=file_name,
        total_rows=len(rows),
        added_count=added_count,
        duplicate_count=duplicate_count,
        error_count=parse_errors,
    )
    messages.success(
        request,
        f"Import zakończony. Wykryty format: {detected_label}. Dodano: {added_count}, duplikaty: {duplicate_count}, błędy: {parse_errors}.",
    )


def build_import_context(request, form, mapping_form=None, mapping_columns=None, mapping_error=None):
    recent_imports = ImportHistory.objects.filter(user=request.user)[:5]
    return {
        "form": form,
        "recent_imports": recent_imports,
        "required_columns": [
            "sleep_date",
            "sleep_duration_minutes",
            "awake_minutes",
            "light_sleep_minutes",
            "deep_sleep_minutes",
            "rem_minutes",
        ],
        "supported_formats": [
            "Własny plik CSV",
            "Mi Fitness CSV",
            "Zepp Life CSV",
        ],
        "mapping_form": mapping_form,
        "mapping_columns": mapping_columns or [],
        "mapping_error": mapping_error,
    }


@login_required
def import_sleep_data_view(request):
    mapping_payload = request.session.get(IMPORT_MAPPING_SESSION_KEY)

    if request.method == "POST" and request.POST.get("step") == "map_columns":
        if not mapping_payload:
            messages.warning(request, "Sesja mapowania wygasła. Wgraj plik jeszcze raz.")
            return redirect("sleep_import")

        available_columns = mapping_payload.get("fieldnames", [])
        form = SleepImportForm()
        mapping_form = SleepImportMappingForm(request.POST, available_columns=available_columns)
        if mapping_form.is_valid():
            manual_mapping = {
                field_name: value
                for field_name, value in mapping_form.cleaned_data.items()
                if value
            }
            try:
                import_result = parse_sleep_csv_content(
                    mapping_payload["decoded_csv"],
                    manual_mapping=manual_mapping,
                    source=SleepRecord.SOURCE_MANUAL_CSV,
                    source_label="Ręczne mapowanie CSV",
                )
            except ValueError as exc:
                return render(
                    request,
                    "sleep/import.html",
                    build_import_context(
                        request,
                        form,
                        mapping_form=mapping_form,
                        mapping_columns=available_columns,
                        mapping_error=str(exc),
                    ),
                )

            request.session.pop(IMPORT_MAPPING_SESSION_KEY, None)
            finalize_sleep_import(request, import_result, mapping_payload["file_name"])
            return redirect("sleep_import")

        return render(
            request,
            "sleep/import.html",
            build_import_context(
                request,
                form,
                mapping_form=mapping_form,
                mapping_columns=available_columns,
            ),
        )

    if request.method == "POST":
        form = SleepImportForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data["file"]
            decoded_csv = decode_sleep_csv(uploaded_file)
            try:
                import_result = parse_sleep_csv_content(decoded_csv)
            except UnrecognizedSleepCsvFormatError as exc:
                request.session[IMPORT_MAPPING_SESSION_KEY] = {
                    "decoded_csv": decoded_csv,
                    "fieldnames": exc.fieldnames,
                    "file_name": uploaded_file.name,
                }
                mapping_form = SleepImportMappingForm(available_columns=exc.fieldnames)
                return render(
                    request,
                    "sleep/import.html",
                    build_import_context(
                        request,
                        form,
                        mapping_form=mapping_form,
                        mapping_columns=exc.fieldnames,
                        mapping_error=str(exc),
                    ),
                )
            except ValueError as exc:
                form.add_error("file", str(exc))
            else:
                request.session.pop(IMPORT_MAPPING_SESSION_KEY, None)
                finalize_sleep_import(request, import_result, uploaded_file.name)
                return redirect("sleep_import")
    else:
        form = SleepImportForm()
        request.session.pop(IMPORT_MAPPING_SESSION_KEY, None)

    return render(request, "sleep/import.html", build_import_context(request, form))


@login_required
def add_sleep_record_view(request):
    if request.method == "POST":
        form = ManualSleepRecordForm(request.POST, user=request.user)
        if form.is_valid():
            sleep_record = form.save(commit=False)
            sleep_record.user = request.user
            sleep_record.source = SleepRecord.SOURCE_MANUAL_CSV
            sleep_record.save()
            messages.success(request, "Noc została dodana ręcznie.")

            goal_minutes = (request.user.profile.sleep_goal_hours or 0) * 60
            if goal_minutes:
                diff = sleep_record.sleep_duration_minutes - goal_minutes
                if diff < 0:
                    messages.warning(
                        request,
                        f"Ta noc trwała {format_minutes_short(sleep_record.sleep_duration_minutes)}, czyli o {format_minutes_short(abs(diff))} krócej niż Twój docelowy czas snu.",
                    )
                elif diff > 0:
                    messages.success(
                        request,
                        f"Ta noc trwała {format_minutes_short(sleep_record.sleep_duration_minutes)}, czyli o {format_minutes_short(diff)} dłużej niż Twój docelowy czas snu.",
                    )

            return redirect("sleep_detail", pk=sleep_record.pk)
    else:
        form = ManualSleepRecordForm(user=request.user)

    return render(request, "sleep/manual_add.html", {"form": form})


@login_required
def sleep_list_view(request):
    queryset = SleepRecord.objects.filter(user=request.user)
    if request.method == "POST":
        selected_ids = request.POST.getlist("selected_records")
        if selected_ids:
            deleted_count, _ = queryset.filter(pk__in=selected_ids).delete()
            messages.success(request, f"Usunięto {deleted_count} zaznaczonych nocy.")
        else:
            messages.warning(request, "Nie zaznaczono żadnej nocy do usunięcia.")
        return redirect("sleep_list")

    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()
    if date_from:
        queryset = queryset.filter(sleep_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(sleep_date__lte=date_to)

    return render(
        request,
        "sleep/sleep_list.html",
        {
            "sleep_records": queryset,
            "date_from": date_from,
            "date_to": date_to,
        },
    )


@login_required
def sleep_detail_view(request, pk):
    sleep_record = get_object_or_404(SleepRecord, pk=pk, user=request.user)
    sleep_note, _ = SleepNote.objects.get_or_create(
        sleep_record=sleep_record,
        defaults={"user": request.user},
    )
    if request.method == "POST":
        note_form = SleepNoteForm(request.POST, instance=sleep_note)
        if note_form.is_valid():
            note = note_form.save(commit=False)
            note.user = request.user
            note.sleep_record = sleep_record
            note.save()
            messages.success(request, "Notatka do nocy została zapisana.")
            return redirect("sleep_detail", pk=sleep_record.pk)
    else:
        note_form = SleepNoteForm(instance=sleep_note)

    auto_evaluation = build_sleep_auto_evaluation(
        sleep_record,
        sleep_note,
        request.user.profile,
    )

    return render(
        request,
        "sleep/sleep_detail.html",
        {
            "sleep_record": sleep_record,
            "note_form": note_form,
            "sleep_note": sleep_note,
            "auto_evaluation": auto_evaluation,
        },
    )


@login_required
def import_history_view(request):
    imports = ImportHistory.objects.filter(user=request.user)
    return render(request, "sleep/import_history.html", {"imports": imports})


def parse_bearer_token(request):
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return request.headers.get("X-API-Key", "").strip()


@csrf_exempt
@require_POST
def sync_sleep_data_api_view(request):
    token = get_sleep_api_token(parse_bearer_token(request))
    if token is None:
        return JsonResponse(
            {"detail": "Brak poprawnego tokenu API."},
            status=401,
        )

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({"detail": "Nieprawid\u0142owy JSON."}, status=400)

    provider = payload.get("provider") or SleepRecord.SOURCE_HEALTH_CONNECT
    supported_providers = {
        SleepRecord.SOURCE_HEALTH_CONNECT,
        SleepRecord.SOURCE_ZEPP_SYNC,
        SleepRecord.SOURCE_ZEPP_LIFE,
    }
    if provider not in supported_providers:
        return JsonResponse({"detail": "Nieobs\u0142ugiwany provider synchronizacji."}, status=400)

    records = payload.get("records")
    if not isinstance(records, list) or not records:
        return JsonResponse({"detail": "Pole records musi zawiera\u0107 list\u0119 rekord\u00f3w."}, status=400)

    device_name = str(payload.get("device_name") or "").strip()[:120]

    try:
        result = sync_sleep_records(
            user=token.user,
            provider=provider,
            records=records,
            device_name=device_name,
        )
    except ValueError as exc:
        mark_sync_error(token.user, provider, str(exc), device_name=device_name)
        return JsonResponse({"detail": str(exc)}, status=400)

    token.last_used_at = timezone.now()
    token.save(update_fields=["last_used_at"])

    return JsonResponse(
        {
            "status": "ok",
            "provider": result["provider"],
            "received_count": result["received_count"],
            "added_count": result["added_count"],
            "updated_count": result["updated_count"],
            "last_synced_at": result["connection"].last_synced_at.isoformat() if result["connection"].last_synced_at else None,
        }
    )

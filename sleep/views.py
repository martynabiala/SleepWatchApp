from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ManualSleepRecordForm, SleepImportForm, SleepNoteForm
from .models import ImportHistory, SleepNote, SleepRecord
from .services import parse_sleep_csv


@login_required
def import_sleep_data_view(request):
    if request.method == "POST":
        form = SleepImportForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.cleaned_data["file"]
            source = form.cleaned_data["source"]
            try:
                rows, parse_errors = parse_sleep_csv(uploaded_file)
            except ValueError as exc:
                form.add_error("file", str(exc))
            else:
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
                                source=source,
                                **row,
                            )
                        added_count += 1
                    except IntegrityError:
                        duplicate_count += 1

                ImportHistory.objects.create(
                    user=request.user,
                    source=source,
                    file_name=uploaded_file.name,
                    total_rows=len(rows),
                    added_count=added_count,
                    duplicate_count=duplicate_count,
                    error_count=parse_errors,
                )
                messages.success(
                    request,
                    f"Import zakończony. Dodano: {added_count}, duplikaty: {duplicate_count}, błędy: {parse_errors}.",
                )
                return redirect("sleep_import")
    else:
        form = SleepImportForm()

    recent_imports = ImportHistory.objects.filter(user=request.user)[:5]
    return render(
        request,
        "sleep/import.html",
        {
            "form": form,
            "recent_imports": recent_imports,
            "required_columns": [
                "sleep_date",
                "sleep_duration_minutes",
                "avg_heart_rate",
                "min_heart_rate",
                "max_heart_rate",
                "min_spo2",
                "movement_level",
            ],
        },
    )


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
            return redirect("sleep_detail", pk=sleep_record.pk)
    else:
        form = ManualSleepRecordForm(user=request.user)

    return render(request, "sleep/manual_add.html", {"form": form})


@login_required
def sleep_list_view(request):
    queryset = SleepRecord.objects.filter(user=request.user)
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

    return render(
        request,
        "sleep/sleep_detail.html",
        {"sleep_record": sleep_record, "note_form": note_form, "sleep_note": sleep_note},
    )


@login_required
def import_history_view(request):
    imports = ImportHistory.objects.filter(user=request.user)
    return render(request, "sleep/import_history.html", {"imports": imports})

import csv
import io
from datetime import datetime

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date as django_parse_date
from django.utils.dateparse import parse_time as django_parse_time

from .models import SleepNote, SleepApiToken, SleepRecord, SleepSyncConnection

REQUIRED_COLUMNS = {
    "sleep_date",
    "sleep_duration_minutes",
    "awake_minutes",
    "light_sleep_minutes",
    "deep_sleep_minutes",
    "rem_minutes",
}

OPTIONAL_COLUMNS = {
    "avg_heart_rate",
    "min_spo2",
}

GENERIC_COLUMN_ALIASES = {
    "sleep_date": {
        "sleep_date",
        "date",
        "night_date",
        "data_nocy",
        "date_of_sleep",
        "sleepday",
    },
    "sleep_duration_minutes": {
        "sleep_duration_minutes",
        "total_sleep_minutes",
        "sleep_minutes",
        "total_sleep",
        "sleep_duration",
        "minutes_asleep",
        "total_minutes_asleep",
    },
    "awake_minutes": {
        "awake_minutes",
        "awake",
        "awake_time",
        "minutes_awake",
        "wake_minutes",
        "time_awake",
    },
    "light_sleep_minutes": {
        "light_sleep_minutes",
        "light_sleep",
        "light_minutes",
        "light",
        "minutes_light_sleep",
    },
    "deep_sleep_minutes": {
        "deep_sleep_minutes",
        "deep_sleep",
        "deep_minutes",
        "deep",
        "minutes_deep_sleep",
    },
    "rem_minutes": {
        "rem_minutes",
        "rem",
        "rem_sleep",
        "rem_sleep_minutes",
        "minutes_rem_sleep",
    },
    "avg_heart_rate": {
        "avg_heart_rate",
        "average_heart_rate",
        "heart_rate_avg",
        "avg_hr",
        "sleep_avg_hr",
    },
    "min_spo2": {
        "min_spo2",
        "spo2_min",
        "lowest_spo2",
        "min_oxygen",
        "min_oxygen_saturation",
    },
}

MI_FITNESS_COLUMN_ALIASES = {
    "sleep_date": {"date", "sleep date"},
    "sleep_duration_minutes": {"sleep minutes", "minutes asleep"},
    "awake_minutes": {"awake minutes", "minutes awake"},
    "light_sleep_minutes": {"light sleep minutes"},
    "deep_sleep_minutes": {"deep sleep minutes"},
    "rem_minutes": {"rem minutes"},
    "avg_heart_rate": {"average heart rate"},
    "min_spo2": {"lowest spo2"},
}

ZEPP_LIFE_COLUMN_ALIASES = {
    "sleep_date": {"sleep date", "night date"},
    "sleep_duration_minutes": {"total sleep", "total sleep minutes"},
    "awake_minutes": {"awake time", "time awake"},
    "light_sleep_minutes": {"light sleep"},
    "deep_sleep_minutes": {"deep sleep"},
    "rem_minutes": {"rem sleep"},
    "avg_heart_rate": {"heart rate avg", "sleep avg hr"},
    "min_spo2": {"spo2 min", "lowest spo2"},
}

IMPORT_FORMATS = [
    {
        "source": SleepRecord.SOURCE_MI_FITNESS,
        "label": "Mi Fitness",
        "aliases": MI_FITNESS_COLUMN_ALIASES,
    },
    {
        "source": SleepRecord.SOURCE_ZEPP_LIFE,
        "label": "Zepp Life",
        "aliases": ZEPP_LIFE_COLUMN_ALIASES,
    },
    {
        "source": SleepRecord.SOURCE_MANUAL_CSV,
        "label": "SleepWatch CSV",
        "aliases": GENERIC_COLUMN_ALIASES,
    },
]


class UnrecognizedSleepCsvFormatError(ValueError):
    def __init__(self, fieldnames):
        self.fieldnames = fieldnames or []
        normalized_fields = ", ".join(self.fieldnames) if self.fieldnames else "brak nagłówków"
        required_list = ", ".join(sorted(REQUIRED_COLUMNS))
        super().__init__(
            "Nie udało się rozpoznać formatu pliku CSV. "
            f"Wykryte nagłówki: {normalized_fields}. "
            "Obsługiwane są formaty: SleepWatch CSV, Mi Fitness i Zepp Life. "
            f"Minimalny zestaw danych to: {required_list}."
        )


def decode_sleep_csv(uploaded_file):
    return uploaded_file.read().decode("utf-8-sig")


def parse_sleep_csv(uploaded_file):
    decoded = decode_sleep_csv(uploaded_file)
    return parse_sleep_csv_content(decoded)


def parse_sleep_csv_content(decoded, manual_mapping=None, source=None, source_label=None):
    reader = csv.DictReader(io.StringIO(decoded))
    fieldnames = reader.fieldnames or []
    if manual_mapping is not None:
        column_mapping = manual_mapping
        missing = REQUIRED_COLUMNS - set(column_mapping)
        if missing:
            raise ValueError("Brak wymaganych kolumn: " + ", ".join(sorted(missing)))
        detected_source = source or SleepRecord.SOURCE_MANUAL_CSV
        detected_label = source_label or "Ręczne mapowanie CSV"
    else:
        detected_format = detect_import_format(fieldnames)
        column_mapping = detected_format["mapping"]
        detected_source = detected_format["source"]
        detected_label = detected_format["label"]

    rows = []
    errors = 0

    for raw_row in reader:
        if not any((value or "").strip() for value in raw_row.values()):
            continue
        try:
            mapped_row = map_row_to_internal_keys(raw_row, column_mapping)
            rows.append(normalize_row(mapped_row, raw_row))
        except ValueError:
            errors += 1

    return {
        "rows": rows,
        "parse_errors": errors,
        "source": detected_source,
        "source_label": detected_label,
        "fieldnames": fieldnames,
    }


def detect_import_format(fieldnames):
    matches = []
    for format_definition in IMPORT_FORMATS:
        mapping = resolve_column_mapping(fieldnames, format_definition["aliases"])
        missing = REQUIRED_COLUMNS - set(mapping)
        matched_optional = len(OPTIONAL_COLUMNS & set(mapping))
        if not missing:
            matches.append(
                {
                    "source": format_definition["source"],
                    "label": format_definition["label"],
                    "mapping": mapping,
                    "score": len(mapping) + matched_optional,
                }
            )

    if matches:
        matches.sort(key=lambda item: item["score"], reverse=True)
        return matches[0]

    raise UnrecognizedSleepCsvFormatError(fieldnames)


def resolve_column_mapping(fieldnames, aliases):
    mapping = {}
    used_raw_columns = set()

    for canonical_name, alias_candidates in aliases.items():
        normalized_aliases = {normalize_column_name(alias) for alias in alias_candidates}
        for raw_name in fieldnames:
            normalized = normalize_column_name(raw_name)
            if normalized in normalized_aliases and raw_name not in used_raw_columns:
                mapping[canonical_name] = raw_name
                used_raw_columns.add(raw_name)
                break

    return mapping


def map_row_to_internal_keys(raw_row, column_mapping):
    mapped = {}
    for canonical_name, raw_name in column_mapping.items():
        mapped[canonical_name] = raw_row.get(raw_name, "")
    return mapped


def normalize_row(row, raw_row):
    sleep_date = parse_date(row["sleep_date"])
    sleep_duration_minutes = parse_required_int(row["sleep_duration_minutes"])
    awake_minutes = parse_required_int(row["awake_minutes"])
    light_sleep_minutes = parse_required_int(row["light_sleep_minutes"])
    deep_sleep_minutes = parse_required_int(row["deep_sleep_minutes"])
    rem_minutes = parse_required_int(row["rem_minutes"])
    avg_heart_rate = parse_optional_int(row.get("avg_heart_rate"))
    min_spo2 = parse_optional_int(row.get("min_spo2"))

    if sleep_duration_minutes <= 0:
        raise ValueError("Czas snu musi być dodatni.")
    if awake_minutes < 0 or light_sleep_minutes < 0 or deep_sleep_minutes < 0 or rem_minutes < 0:
        raise ValueError("Czasy faz snu nie mogą być ujemne.")

    phase_total = light_sleep_minutes + deep_sleep_minutes + rem_minutes
    if phase_total > sleep_duration_minutes + 30:
        raise ValueError("Suma faz snu nie może znacząco przekraczać całkowitego czasu snu.")

    return {
        "sleep_date": sleep_date,
        "sleep_duration_minutes": sleep_duration_minutes,
        "awake_minutes": awake_minutes,
        "light_sleep_minutes": light_sleep_minutes,
        "deep_sleep_minutes": deep_sleep_minutes,
        "rem_minutes": rem_minutes,
        "avg_heart_rate": avg_heart_rate,
        "min_spo2": min_spo2,
        "raw_data": raw_row,
    }


def normalize_column_name(value):
    return "".join(char for char in (value or "").strip().lower() if char.isalnum())


def parse_date(value):
    value = (value or "").strip()
    for date_format in ("%Y-%m-%d", "%d.%m.%Y", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue
    raise ValueError("Nieprawidłowa data.")


def parse_required_int(value):
    parsed = parse_optional_int(value)
    if parsed is None:
        raise ValueError("Brak wymaganej wartości liczbowej.")
    return parsed


def parse_optional_int(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        parsed = int(round(float(value)))
        if parsed < 0:
            raise ValueError("Warto\u015b\u0107 nie mo\u017ce by\u0107 ujemna.")
        return parsed

    value = str(value).strip()
    if not value:
        return None
    normalized = value.replace(",", ".")
    parsed = int(round(float(normalized)))
    if parsed < 0:
        raise ValueError("Warto\u015b\u0107 nie mo\u017ce by\u0107 ujemna.")
    return parsed


def get_sleep_api_token(raw_token):
    token = (raw_token or "").strip()
    if not token:
        return None
    try:
        return SleepApiToken.objects.select_related("user").get(key=token)
    except SleepApiToken.DoesNotExist:
        return None


def sync_sleep_records(user, provider, records, device_name=""):
    normalized_provider = provider or SleepRecord.SOURCE_HEALTH_CONNECT
    added_count = 0
    updated_count = 0

    connection, _ = SleepSyncConnection.objects.get_or_create(
        user=user,
        provider=normalized_provider,
        defaults={"last_device_name": device_name},
    )

    for payload in records:
        normalized_record = normalize_sync_record(payload, normalized_provider, device_name)
        external_record_id = normalized_record.pop("external_record_id", "")

        with transaction.atomic():
            record = find_existing_synced_record(user, normalized_provider, external_record_id, normalized_record["sleep_date"])
            if record is None:
                SleepRecord.objects.create(
                    user=user,
                    source=normalized_provider,
                    external_record_id=external_record_id,
                    **normalized_record,
                )
                added_count += 1
            else:
                for field_name, value in normalized_record.items():
                    setattr(record, field_name, value)
                if external_record_id:
                    record.external_record_id = external_record_id
                record.source = normalized_provider
                record.save()
                updated_count += 1

    connection.is_enabled = True
    connection.last_synced_at = timezone.now()
    connection.last_imported_count = len(records)
    connection.last_error = ""
    connection.last_device_name = device_name
    connection.save()

    return {
        "connection": connection,
        "added_count": added_count,
        "updated_count": updated_count,
        "received_count": len(records),
    }


def mark_sync_error(user, provider, error_message, device_name=""):
    connection, _ = SleepSyncConnection.objects.get_or_create(
        user=user,
        provider=provider,
        defaults={"last_device_name": device_name},
    )
    connection.is_enabled = True
    connection.last_error = error_message
    if device_name:
        connection.last_device_name = device_name
    connection.save(update_fields=["is_enabled", "last_error", "last_device_name", "updated_at"])
    return connection


def find_existing_synced_record(user, provider, external_record_id, sleep_date):
    if external_record_id:
        record = SleepRecord.objects.filter(
            user=user,
            source=provider,
            external_record_id=external_record_id,
        ).first()
        if record:
            return record

    return SleepRecord.objects.filter(
        user=user,
        source=provider,
        sleep_date=sleep_date,
    ).first()


def normalize_sync_record(payload, provider, device_name=""):
    if not isinstance(payload, dict):
        raise ValueError("Ka\u017cdy rekord synchronizacji musi by\u0107 obiektem JSON.")

    sleep_date = parse_sync_date(payload.get("sleep_date"))
    sleep_duration_minutes = parse_required_int(payload.get("sleep_duration_minutes"))

    normalized = {
        "sleep_date": sleep_date,
        "sleep_duration_minutes": sleep_duration_minutes,
        "bedtime": parse_sync_time(payload.get("bedtime")),
        "wake_time": parse_sync_time(payload.get("wake_time")),
        "awakenings_count": parse_optional_int(payload.get("awakenings_count")),
        "awake_minutes": parse_optional_int(payload.get("awake_minutes")),
        "light_sleep_minutes": parse_optional_int(payload.get("light_sleep_minutes")),
        "deep_sleep_minutes": parse_optional_int(payload.get("deep_sleep_minutes")),
        "rem_minutes": parse_optional_int(payload.get("rem_minutes")),
        "avg_heart_rate": parse_optional_int(payload.get("avg_heart_rate")),
        "min_spo2": parse_optional_int(payload.get("min_spo2")),
        "raw_data": payload.get("raw_data", payload),
        "synced_at": timezone.now(),
        "device_name": (payload.get("device_name") or device_name or "")[:120],
    }
    normalized["external_record_id"] = str(payload.get("external_id") or payload.get("external_record_id") or "").strip()

    if sleep_duration_minutes <= 0:
        raise ValueError("Pole sleep_duration_minutes musi by\u0107 dodatnie.")

    if (
        normalized["light_sleep_minutes"] is not None
        and normalized["deep_sleep_minutes"] is not None
        and normalized["rem_minutes"] is not None
    ):
        phase_total = (
            normalized["light_sleep_minutes"]
            + normalized["deep_sleep_minutes"]
            + normalized["rem_minutes"]
        )
        if phase_total > sleep_duration_minutes + 30:
            raise ValueError("Suma faz snu nie mo\u017ce znacz\u0105co przekracza\u0107 ca\u0142kowitego czasu snu.")

    return normalized


def parse_sync_date(value):
    if hasattr(value, "isoformat"):
        return value

    parsed = django_parse_date(str(value or "").strip())
    if parsed:
        return parsed

    return parse_date(str(value or "").strip())


def parse_sync_time(value):
    if value in (None, ""):
        return None
    if hasattr(value, "isoformat") and not isinstance(value, str):
        return value

    parsed = django_parse_time(str(value).strip())
    if parsed:
        return parsed

    for time_format in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(str(value).strip(), time_format).time()
        except ValueError:
            continue
    raise ValueError("Nieprawid\u0142owy format godziny. U\u017cyj HH:MM lub HH:MM:SS.")


def build_sleep_auto_evaluation(sleep_record, sleep_note, profile):
    score = 72
    reasons = []
    goal_minutes = (profile.sleep_goal_hours or 8) * 60
    sleep_diff = sleep_record.sleep_duration_minutes - goal_minutes

    if sleep_diff <= -120:
        score -= 24
        reasons.append("sen był wyraźnie krótszy od celu")
    elif sleep_diff <= -60:
        score -= 16
        reasons.append("sen był krótszy od celu")
    elif sleep_diff <= -30:
        score -= 8
        reasons.append("sen był lekko krótszy od celu")
    elif abs(sleep_diff) <= 30:
        score += 4
        reasons.append("czas snu był blisko celu")
    elif sleep_diff >= 90:
        score -= 4
        reasons.append("sen był wyraźnie dłuższy niż zwykle")

    if sleep_record.awake_minutes is not None:
        if sleep_record.awake_minutes >= 60:
            score -= 12
            reasons.append("czas czuwania był dość długi")
        elif sleep_record.awake_minutes >= 30:
            score -= 6
            reasons.append("pojawiło się trochę czuwania w nocy")
        elif sleep_record.awake_minutes <= 15:
            score += 3
            reasons.append("noc była dość ciągła")

    if sleep_record.awakenings_count is not None:
        if sleep_record.awakenings_count >= 4:
            score -= 10
            reasons.append("wystąpiło sporo wybudzeń")
        elif sleep_record.awakenings_count >= 2:
            score -= 5
            reasons.append("pojawiło się kilka wybudzeń")
        elif sleep_record.awakenings_count == 0:
            score += 3
            reasons.append("sen był nieprzerywany")

    if sleep_record.sleep_duration_minutes:
        deep_share = (sleep_record.deep_sleep_minutes or 0) / sleep_record.sleep_duration_minutes
        rem_share = (sleep_record.rem_minutes or 0) / sleep_record.sleep_duration_minutes

        if deep_share >= 0.18:
            score += 4
            reasons.append("udział snu głębokiego wyglądał dobrze")
        elif 0 < deep_share < 0.1:
            score -= 6
            reasons.append("snu głębokiego było niewiele")

        if rem_share >= 0.18:
            score += 3
            reasons.append("REM wyglądał stabilnie")
        elif 0 < rem_share < 0.12:
            score -= 4
            reasons.append("REM był raczej krótki")

    if sleep_record.min_spo2 is not None:
        if sleep_record.min_spo2 < 90:
            score -= 20
            reasons.append("minimalne SpO2 było niskie")
        elif sleep_record.min_spo2 < 93:
            score -= 10
            reasons.append("minimalne SpO2 było poniżej optymalnego poziomu")
        else:
            score += 3
            reasons.append("SpO2 wyglądało stabilnie")

    if sleep_record.avg_heart_rate is not None:
        if sleep_record.avg_heart_rate >= 70:
            score -= 12
            reasons.append("średnie tętno było podwyższone")
        elif sleep_record.avg_heart_rate >= 63:
            score -= 6
            reasons.append("średnie tętno było trochę wyższe")
        elif sleep_record.avg_heart_rate <= 58:
            score += 4
            reasons.append("średnie tętno było spokojne")

    if sleep_note:
        if sleep_note.caffeine_used:
            if sleep_note.caffeine_last_time and sleep_note.caffeine_last_time.hour >= 16:
                score -= 8
                reasons.append("pojawiła się kofeina po 16:00")
            elif sleep_note.caffeine_count and sleep_note.caffeine_count >= 3:
                score -= 5
                reasons.append("kofeina pojawiła się kilka razy")
        if sleep_note.alcohol:
            score -= 12
            reasons.append("pojawił się alkohol")
        if sleep_note.training_done and sleep_note.training_level == SleepNote.TRAINING_HARD:
            score -= 5
            reasons.append("trening był ciężki")
        elif sleep_note.training_done and sleep_note.training_level == SleepNote.TRAINING_LIGHT:
            score += 2
            reasons.append("lekki trening mógł pomóc regeneracji")
        if sleep_note.stress_level is not None:
            if sleep_note.stress_level >= 8:
                score -= 15
                reasons.append("poziom stresu był bardzo wysoki")
            elif sleep_note.stress_level >= 6:
                score -= 8
                reasons.append("poziom stresu był podwyższony")
            elif sleep_note.stress_level <= 3:
                score += 3
                reasons.append("poziom stresu był niski")

    score = max(0, min(100, score))
    if score >= 75:
        label = "Dobra noc"
        tone = "positive"
    elif score >= 50:
        label = "Średnia noc"
        tone = "neutral"
    else:
        label = "Słaba noc"
        tone = "warning"

    return {
        "score": score,
        "label": label,
        "tone": tone,
        "summary": ", ".join(reasons[:3]) if reasons else "Za mało danych do dokładniejszego uzasadnienia.",
    }

import csv
import io
from datetime import datetime

from .models import SleepRecord

REQUIRED_COLUMNS = {
    "sleep_date",
    "sleep_duration_minutes",
    "avg_heart_rate",
    "min_heart_rate",
    "max_heart_rate",
    "min_spo2",
    "movement_level",
}

MOVEMENT_MAPPING = {
    "low": SleepRecord.MOVEMENT_LOW,
    "niski": SleepRecord.MOVEMENT_LOW,
    "medium": SleepRecord.MOVEMENT_MEDIUM,
    "sredni": SleepRecord.MOVEMENT_MEDIUM,
    "średni": SleepRecord.MOVEMENT_MEDIUM,
    "high": SleepRecord.MOVEMENT_HIGH,
    "wysoki": SleepRecord.MOVEMENT_HIGH,
    "unknown": SleepRecord.MOVEMENT_UNKNOWN,
    "brak": SleepRecord.MOVEMENT_UNKNOWN,
    "brak danych": SleepRecord.MOVEMENT_UNKNOWN,
    "": SleepRecord.MOVEMENT_UNKNOWN,
}


def parse_sleep_csv(uploaded_file):
    decoded = uploaded_file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(decoded))
    columns = set(reader.fieldnames or [])
    missing = REQUIRED_COLUMNS - columns
    if missing:
        raise ValueError(
            "Brak wymaganych kolumn: " + ", ".join(sorted(missing))
        )

    rows = []
    errors = 0

    for raw_row in reader:
        if not any((value or "").strip() for value in raw_row.values()):
            continue
        try:
            rows.append(normalize_row(raw_row))
        except ValueError:
            errors += 1

    return rows, errors


def normalize_row(row):
    sleep_date = datetime.strptime(row["sleep_date"].strip(), "%Y-%m-%d").date()
    sleep_duration_minutes = int(row["sleep_duration_minutes"])
    avg_heart_rate = parse_optional_int(row.get("avg_heart_rate"))
    min_heart_rate = parse_optional_int(row.get("min_heart_rate"))
    max_heart_rate = parse_optional_int(row.get("max_heart_rate"))
    min_spo2 = parse_optional_int(row.get("min_spo2"))
    movement_level = map_movement_level(row.get("movement_level", ""))

    if sleep_duration_minutes <= 0:
        raise ValueError("Czas snu musi byc dodatni.")

    return {
        "sleep_date": sleep_date,
        "sleep_duration_minutes": sleep_duration_minutes,
        "avg_heart_rate": avg_heart_rate,
        "min_heart_rate": min_heart_rate,
        "max_heart_rate": max_heart_rate,
        "min_spo2": min_spo2,
        "movement_level": movement_level,
        "raw_data": row,
    }


def parse_optional_int(value):
    value = (value or "").strip()
    if not value:
        return None
    parsed = int(value)
    if parsed < 0:
        raise ValueError("Wartosc nie moze byc ujemna.")
    return parsed


def map_movement_level(value):
    normalized = (value or "").strip().lower()
    if normalized not in MOVEMENT_MAPPING:
        raise ValueError("Nieznany poziom ruchu.")
    return MOVEMENT_MAPPING[normalized]

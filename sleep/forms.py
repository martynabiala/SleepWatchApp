from datetime import datetime, timedelta

from django import forms

from .models import SleepNote, SleepRecord


class SleepImportForm(forms.Form):
    file = forms.FileField(label="Plik CSV")

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        if not uploaded_file.name.lower().endswith(".csv"):
            raise forms.ValidationError("Na razie obsługiwany jest tylko plik CSV.")
        return uploaded_file


class SleepImportMappingForm(forms.Form):
    MAPPING_FIELDS = (
        ("sleep_date", "Kolumna z datą snu"),
        ("sleep_duration_minutes", "Kolumna z całkowitym czasem snu"),
        ("awake_minutes", "Kolumna z czasem czuwania"),
        ("light_sleep_minutes", "Kolumna z czasem snu lekkiego"),
        ("deep_sleep_minutes", "Kolumna z czasem snu głębokiego"),
        ("rem_minutes", "Kolumna z czasem REM"),
        ("avg_heart_rate", "Kolumna ze średnim tętnem"),
        ("min_spo2", "Kolumna z minimalnym SpO2"),
    )

    def __init__(self, *args, available_columns=None, **kwargs):
        super().__init__(*args, **kwargs)
        choices = [("", "---------")]
        choices.extend((column, column) for column in (available_columns or []))
        required_fields = {
            "sleep_date",
            "sleep_duration_minutes",
            "awake_minutes",
            "light_sleep_minutes",
            "deep_sleep_minutes",
            "rem_minutes",
        }

        for field_name, label in self.MAPPING_FIELDS:
            self.fields[field_name] = forms.ChoiceField(
                label=label,
                choices=choices,
                required=field_name in required_fields,
            )

    def clean(self):
        cleaned_data = super().clean()
        selected_columns = {}

        for field_name, _ in self.MAPPING_FIELDS:
            value = cleaned_data.get(field_name)
            if not value:
                continue
            if value in selected_columns:
                self.add_error(
                    field_name,
                    f'Kolumna {value} jest już użyta dla pola "{selected_columns[value]}".',
                )
            else:
                selected_columns[value] = self.fields[field_name].label

        return cleaned_data


class ManualSleepRecordForm(forms.ModelForm):
    bedtime = forms.TimeField(
        label="Godzina zaśnięcia",
        required=True,
        help_text="Na przykład 23:15.",
        widget=forms.TimeInput(attrs={"type": "time"}),
    )
    wake_time = forms.TimeField(
        label="Godzina pobudki",
        required=True,
        help_text="Na przykład 07:00.",
        widget=forms.TimeInput(attrs={"type": "time"}),
    )

    class Meta:
        model = SleepRecord
        fields = (
            "sleep_date",
            "bedtime",
            "wake_time",
            "awakenings_count",
        )
        labels = {
            "sleep_date": "Data nocy",
            "awakenings_count": "Liczba wybudzeń",
        }
        help_texts = {
            "awakenings_count": "Opcjonalnie, jeśli pamiętasz ile razy obudziłaś się w nocy.",
        }
        widgets = {
            "sleep_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_sleep_date(self):
        sleep_date = self.cleaned_data["sleep_date"]
        if self.user and SleepRecord.objects.filter(user=self.user, sleep_date=sleep_date).exists():
            raise forms.ValidationError("Masz już zapisaną noc dla tej daty.")
        return sleep_date

    def clean(self):
        cleaned_data = super().clean()
        bedtime = cleaned_data.get("bedtime")
        wake_time = cleaned_data.get("wake_time")

        if bedtime and wake_time:
            duration = self.calculate_duration_minutes(bedtime, wake_time)
            if duration <= 0:
                self.add_error("wake_time", "Godzina pobudki musi być późniejsza niż zaśnięcie.")
            elif duration < 60:
                self.add_error("wake_time", "Wyliczony czas snu jest zbyt krótki.")
            elif duration > 16 * 60:
                self.add_error("wake_time", "Wyliczony czas snu jest zbyt długi.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.sleep_duration_minutes = self.calculate_duration_minutes(
            self.cleaned_data["bedtime"],
            self.cleaned_data["wake_time"],
        )
        if commit:
            instance.save()
        return instance

    @staticmethod
    def calculate_duration_minutes(bedtime, wake_time):
        base_date = datetime(2000, 1, 1)
        bedtime_dt = datetime.combine(base_date.date(), bedtime)
        wake_dt = datetime.combine(base_date.date(), wake_time)
        if wake_dt <= bedtime_dt:
            wake_dt += timedelta(days=1)
        return int((wake_dt - bedtime_dt).total_seconds() // 60)


class SleepNoteForm(forms.ModelForm):
    stress_level = forms.IntegerField(
        label="Jak oceniasz poziom stresu tego dnia?",
        min_value=0,
        max_value=10,
        required=False,
        widget=forms.NumberInput(
            attrs={
                "min": 0,
                "max": 10,
                "step": 1,
                "placeholder": "0-10",
            }
        ),
    )
    caffeine_used = forms.TypedChoiceField(
        label="Kofeina tego dnia",
        choices=(("False", "Nie"), ("True", "Tak")),
        coerce=lambda value: value in (True, "True", "true", "1", "Tak", "on"),
        empty_value=False,
    )
    caffeine_last_time = forms.TimeField(
        label="Godzina ostatniej dawki kofeiny",
        required=False,
        widget=forms.TimeInput(attrs={"type": "time"}),
    )
    caffeine_count = forms.IntegerField(
        label="Liczba wypitych napojów z kofeiną",
        required=False,
        min_value=1,
        max_value=10,
    )
    nap_taken = forms.TypedChoiceField(
        label="Drzemka tego dnia",
        choices=(("False", "Nie"), ("True", "Tak")),
        coerce=lambda value: value in (True, "True", "true", "1", "Tak", "on"),
        empty_value=False,
        required=False,
    )
    nap_time = forms.TimeField(
        label="Godzina drzemki",
        required=False,
        widget=forms.TimeInput(attrs={"type": "time"}),
    )
    alcohol = forms.TypedChoiceField(
        label="Alkohol tego dnia",
        choices=(("False", "Nie"), ("True", "Tak")),
        coerce=lambda value: value in (True, "True", "true", "1", "Tak", "on"),
        empty_value=False,
        required=False,
    )
    training_done = forms.TypedChoiceField(
        label="Trening tego dnia",
        choices=(("False", "Nie"), ("True", "Tak")),
        coerce=lambda value: value in (True, "True", "true", "1", "Tak", "on"),
        empty_value=False,
    )
    training_time = forms.TimeField(
        label="Godzina treningu",
        required=False,
        widget=forms.TimeInput(attrs={"type": "time"}),
    )

    class Meta:
        model = SleepNote
        fields = (
            "sleep_quality",
            "caffeine_used",
            "caffeine_last_time",
            "caffeine_count",
            "nap_taken",
            "nap_time",
            "alcohol",
            "training_done",
            "training_level",
            "training_time",
            "stress_level",
            "note_text",
        )
        labels = {
            "training_level": "Jaki był twój trening?",
            "note_text": "Dodatkowe informacje",
        }
        widgets = {
            "note_text": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        cleaned_data = super().clean()
        caffeine_used = cleaned_data.get("caffeine_used")
        caffeine_last_time = cleaned_data.get("caffeine_last_time")
        caffeine_count = cleaned_data.get("caffeine_count")
        nap_taken = cleaned_data.get("nap_taken")
        nap_time = cleaned_data.get("nap_time")
        training_done = cleaned_data.get("training_done")
        training_level = cleaned_data.get("training_level")
        training_time = cleaned_data.get("training_time")

        if caffeine_used:
            if not caffeine_last_time:
                self.add_error("caffeine_last_time", "Podaj godzinę ostatniej dawki kofeiny.")
            if not caffeine_count:
                self.add_error("caffeine_count", "Podaj liczbę wypitych napojów z kofeiną.")
        else:
            cleaned_data["caffeine_last_time"] = None
            cleaned_data["caffeine_count"] = None

        if nap_taken:
            if not nap_time:
                self.add_error("nap_time", "Podaj godzinę drzemki.")
        else:
            cleaned_data["nap_time"] = None

        if training_done:
            if training_level in (None, "", SleepNote.TRAINING_NONE):
                self.add_error("training_level", "Wybierz intensywność treningu.")
            if not training_time:
                self.add_error("training_time", "Podaj godzinę treningu.")
        else:
            cleaned_data["training_level"] = SleepNote.TRAINING_NONE
            cleaned_data["training_time"] = None

        return cleaned_data

    def clean_stress_level(self):
        stress_level = self.cleaned_data.get("stress_level")
        if stress_level is not None and not 0 <= stress_level <= 10:
            raise forms.ValidationError("Poziom stresu musi być w zakresie 0-10.")
        return stress_level

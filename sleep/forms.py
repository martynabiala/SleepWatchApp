from django import forms

from .models import ImportHistory, SleepNote, SleepRecord


class SleepImportForm(forms.Form):
    source = forms.ChoiceField(
        label="Źródło danych",
        choices=ImportHistory.IMPORT_SOURCE_CHOICES,
    )
    file = forms.FileField(label="Plik CSV")

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        if not uploaded_file.name.lower().endswith(".csv"):
            raise forms.ValidationError("Na razie obsługiwany jest tylko plik CSV.")
        return uploaded_file


class ManualSleepRecordForm(forms.ModelForm):
    class Meta:
        model = SleepRecord
        fields = (
            "sleep_date",
            "sleep_duration_minutes",
            "avg_heart_rate",
            "min_heart_rate",
            "max_heart_rate",
            "min_spo2",
            "movement_level",
        )
        labels = {
            "sleep_date": "Data nocy",
            "sleep_duration_minutes": "Czas snu (minuty)",
            "avg_heart_rate": "Średnie tętno",
            "min_heart_rate": "Minimalne tętno",
            "max_heart_rate": "Maksymalne tętno",
            "min_spo2": "Minimalne SpO2",
            "movement_level": "Ruch w nocy",
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


class SleepNoteForm(forms.ModelForm):
    stress_level = forms.IntegerField(
        label="Poziom stresu",
        min_value=0,
        max_value=10,
        required=False,
        help_text="Skala od 0 do 10.",
        widget=forms.NumberInput(
            attrs={
                "min": 0,
                "max": 10,
                "step": 1,
                "placeholder": "0-10",
            }
        ),
    )

    class Meta:
        model = SleepNote
        fields = (
            "sleep_quality",
            "caffeine_after_16",
            "alcohol",
            "training_level",
            "stress_level",
            "note_text",
        )
        widgets = {
            "note_text": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_stress_level(self):
        stress_level = self.cleaned_data.get("stress_level")
        if stress_level is not None and not 0 <= stress_level <= 10:
            raise forms.ValidationError("Poziom stresu musi być w zakresie 0-10.")
        return stress_level

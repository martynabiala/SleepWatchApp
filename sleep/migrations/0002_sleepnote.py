from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("sleep", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SleepNote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sleep_quality", models.CharField(choices=[("bad", "Slaba noc"), ("neutral", "Neutralna noc"), ("good", "Dobra noc")], default="neutral", max_length=10, verbose_name="Jakosc snu")),
                ("caffeine_after_16", models.BooleanField(default=False, verbose_name="Kofeina po 16:00")),
                ("alcohol", models.BooleanField(default=False, verbose_name="Alkohol")),
                ("training_level", models.CharField(choices=[("none", "Brak"), ("light", "Lekki"), ("moderate", "Sredni"), ("hard", "Ciezki")], default="none", max_length=10, verbose_name="Trening")),
                ("stress_level", models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="Poziom stresu")),
                ("note_text", models.TextField(blank=True, verbose_name="Notatka")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("sleep_record", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="note", to="sleep.sleeprecord")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sleep_notes", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Notatka do nocy",
                "verbose_name_plural": "Notatki do nocy",
            },
        ),
    ]

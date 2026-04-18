from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_alter_userprofile_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="active_hypothesis",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Bez aktywnej hipotezy"),
                    ("caffeine", "Sprawdzam wpływ kofeiny na sen"),
                    ("stress", "Sprawdzam wpływ stresu na sen"),
                    ("nap", "Sprawdzam wpływ drzemek na nocny sen"),
                    ("alcohol", "Sprawdzam wpływ alkoholu na sen"),
                    ("training", "Sprawdzam wpływ treningu na sen"),
                ],
                default="",
                max_length=20,
                verbose_name="Aktywna hipoteza miesiaca",
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="active_hypothesis_started_at",
            field=models.DateField(
                blank=True,
                null=True,
                verbose_name="Data rozpoczecia hipotezy",
            ),
        ),
    ]

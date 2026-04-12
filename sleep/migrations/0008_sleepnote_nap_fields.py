from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sleep", "0007_sleepnote_caffeine_details"),
    ]

    operations = [
        migrations.AddField(
            model_name="sleepnote",
            name="nap_taken",
            field=models.BooleanField(default=False, verbose_name="Czy była drzemka"),
        ),
        migrations.AddField(
            model_name="sleepnote",
            name="nap_time",
            field=models.TimeField(blank=True, null=True, verbose_name="Godzina drzemki"),
        ),
    ]

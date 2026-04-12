from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sleep", "0005_sleeprecord_awakenings_count"),
    ]

    operations = [
        migrations.AddField(
            model_name="sleepnote",
            name="training_done",
            field=models.BooleanField(default=False, verbose_name="Czy był trening"),
        ),
        migrations.AddField(
            model_name="sleepnote",
            name="training_time",
            field=models.TimeField(blank=True, null=True, verbose_name="Godzina treningu"),
        ),
    ]

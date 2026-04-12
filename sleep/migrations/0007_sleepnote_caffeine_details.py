from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sleep", "0006_sleepnote_training_done_sleepnote_training_time"),
    ]

    operations = [
        migrations.AddField(
            model_name="sleepnote",
            name="caffeine_count",
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="Ile razy była kofeina"),
        ),
        migrations.AddField(
            model_name="sleepnote",
            name="caffeine_last_time",
            field=models.TimeField(blank=True, null=True, verbose_name="Godzina ostatniej kofeiny"),
        ),
        migrations.AddField(
            model_name="sleepnote",
            name="caffeine_used",
            field=models.BooleanField(default=False, verbose_name="Czy była kofeina"),
        ),
        migrations.RemoveField(
            model_name="sleepnote",
            name="caffeine_after_16",
        ),
    ]

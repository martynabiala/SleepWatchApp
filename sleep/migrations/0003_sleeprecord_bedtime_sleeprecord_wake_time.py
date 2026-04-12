from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sleep", "0002_sleepnote"),
    ]

    operations = [
        migrations.AddField(
            model_name="sleeprecord",
            name="bedtime",
            field=models.TimeField(blank=True, null=True, verbose_name="Godzina zaśnięcia"),
        ),
        migrations.AddField(
            model_name="sleeprecord",
            name="wake_time",
            field=models.TimeField(blank=True, null=True, verbose_name="Godzina pobudki"),
        ),
    ]

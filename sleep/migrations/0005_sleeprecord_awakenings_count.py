from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sleep", "0004_alter_importhistory_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="sleeprecord",
            name="awakenings_count",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                verbose_name="Liczba wybudzeń",
            ),
        ),
    ]

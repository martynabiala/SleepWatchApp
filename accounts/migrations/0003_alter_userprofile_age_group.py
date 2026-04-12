from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_remove_userprofile_bio"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="age_group",
            field=models.CharField(
                blank=True,
                choices=[
                    ("under_18", "Poniżej 18 lat"),
                    ("18-25", "18-25 lat"),
                    ("26-35", "26-35 lat"),
                    ("36-50", "36-50 lat"),
                    ("51+", "51+ lat"),
                ],
                max_length=10,
                verbose_name="Grupa wiekowa",
            ),
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_userprofile_avatar"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="preferred_sync_source",
            field=models.CharField(
                choices=[("health_connect", "Health Connect"), ("zepp_life", "Zepp Life")],
                default="health_connect",
                max_length=20,
                verbose_name="Preferowane zrodlo synchronizacji",
            ),
        ),
    ]

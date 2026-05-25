from django.db import migrations, models


def move_phone_sync_to_csv(apps, schema_editor):
    UserProfile = apps.get_model("accounts", "UserProfile")
    UserProfile.objects.filter(preferred_sync_source="health_connect").update(preferred_sync_source="manual_csv")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0016_userprofile_avatar_image_data"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="preferred_sync_source",
            field=models.CharField(
                choices=[
                    ("health_connect", "Synchronizacja z telefonu"),
                    ("manual_csv", "Import pliku CSV"),
                ],
                default="manual_csv",
                max_length=20,
                verbose_name="Preferowane źródło synchronizacji",
            ),
        ),
        migrations.RunPython(move_phone_sync_to_csv, migrations.RunPython.noop),
    ]

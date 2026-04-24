from django.db import migrations, models


def migrate_legacy_zepp_choice(apps, schema_editor):
    UserProfile = apps.get_model("accounts", "UserProfile")
    UserProfile.objects.filter(preferred_sync_source="zepp_life").update(
        preferred_sync_source="health_connect"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0010_alter_userprofile_options_and_more"),
    ]

    operations = [
        migrations.RunPython(migrate_legacy_zepp_choice, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="userprofile",
            name="preferred_sync_source",
            field=models.CharField(
                choices=[
                    ("health_connect", "Synchronizacja z telefonu"),
                    ("manual_csv", "Import pliku CSV"),
                ],
                default="health_connect",
                max_length=20,
                verbose_name="Preferowane źródło synchronizacji",
            ),
        ),
    ]

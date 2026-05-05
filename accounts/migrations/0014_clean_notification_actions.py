from django.db import migrations


def clean_confirmation_actions(apps, schema_editor):
    UserNotification = apps.get_model("accounts", "UserNotification")
    UserNotification.objects.filter(
        dedupe_key__in=["profile-updated", "sync-source-updated"],
    ).update(action_url="")
    UserNotification.objects.filter(kind="support").update(action_url="")


def restore_confirmation_actions(apps, schema_editor):
    UserNotification = apps.get_model("accounts", "UserNotification")
    UserNotification.objects.filter(dedupe_key="profile-updated").update(
        action_url="/profil/"
    )
    UserNotification.objects.filter(dedupe_key="sync-source-updated").update(
        action_url="/zrodla-danych/"
    )
    UserNotification.objects.filter(kind="support").update(
        action_url="/pomoc/zglos-blad/"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0013_usernotification"),
    ]

    operations = [
        migrations.RunPython(clean_confirmation_actions, restore_confirmation_actions),
    ]

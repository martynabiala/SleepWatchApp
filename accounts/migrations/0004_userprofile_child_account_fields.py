from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_alter_userprofile_age_group"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="is_child_account",
            field=models.BooleanField(default=False, verbose_name="Czy konto dziecka"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="parent_email",
            field=models.EmailField(blank=True, max_length=254, verbose_name="E-mail rodzica"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="parental_consent_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Data zgody rodzica"),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="parental_consent_granted",
            field=models.BooleanField(default=False, verbose_name="Zgoda rodzica"),
        ),
    ]

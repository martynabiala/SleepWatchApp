from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_userprofile_child_account_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="avatar",
            field=models.CharField(
                choices=[
                    ("moon", "Księżyc"),
                    ("star", "Gwiazda"),
                    ("cloud", "Chmurka"),
                    ("sun", "Słońce"),
                    ("leaf", "Listek"),
                    ("heart", "Serce"),
                ],
                default="moon",
                max_length=20,
                verbose_name="Awatar",
            ),
        ),
    ]
